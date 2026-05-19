//==============================================================================
/* leader_shivaji.xs

   Shivaji Bhonsle (Chhatrapati Shivaji Maharaj) - Maratha founder personality.

   Historical doctrine:
     - Ganimi Kava (guerilla warfare): Shivaji's signature was hit-and-run
       cavalry raids from hilltop forts against larger Mughal armies.
       Mapped to a strong cavalry bias and a forward-base posture from
       Colonial on.
     - Hill-fort network (Raigad, Rajgad, Pratapgad, Sinhagad): Maratha
       power was a constellation of fortresses, not a capital and a field
       army. Mapped to a high tower count, fort-friendly behavior, and a
       Compact Fortified Core build style.
     - Mavle infantry and Sepoy musket: hardy hill-country infantry
       backbone behind the cavalry sweep. Mapped to a real infantry share
       behind the cavalry weight, not an all-cavalry composition.
     - Naval Maratha: Shivaji built India's first major modern navy
       (Sindhudurg, Vijaydurg). Standard naval-AI handles this; the land
       personality leans Distributed for forward bases on captured ground.
     - Religious tolerance + drumbeat statecraft: army stays loyal because
       it is paid and respected. The civ's caste-economy (Wonder loyalty,
       Sepoy from Caravanserai) maps to a moderate Trade Route lean.
*/
//==============================================================================

bool gShivajiRulesEnabled = false;

void initLeaderShivaji(void)
{
   llVerboseEcho("A New World: activating Shivaji Maharaj personality.");

   llSetBalancedPersonality();
   btRushBoom = 0.0;              // Light boom; the raids open early.
   btOffenseDefense = 0.55;
   btBiasTrade = 0.2;             // Caravanserai economy.
   btBiasNative = 0.2;
   llSetMilitaryFocus(0.55, 0.6, 0.2);  // Cavalry-leaning composition.

   // LL-BUILD-STYLE-BEGIN
   // Spec doctrine = Highland Citadel (hill-fort fortress ring). Shivaji's
   // Maratha hill-fort network maps to the Citadel helper, not the Shrine
   // helper (which leaves walls off entirely).
   llUseHighlandCitadelStyle(2);
   gLLEconomicDistanceMultiplier = 1.10;
   llSetBuildStrongpointProfile(2, 1, 2, false);
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.78, 0.22, 2, 4.0);

   cvOkToBuildForts = true;
   cvMaxTowers = 6;               // Hill-fort network.
   cvMaxArmyPop = 115;

   gShivajiRulesEnabled = true;
   llLogLeaderState("Shivaji initialized");
   llProbe("meta.leader_init", "leader=shivaji");
}

//------------------------------------------------------------------------------
// Discovery: Wadi village boom. Settler push and Caravanserai placement.
//------------------------------------------------------------------------------
rule shivajiVillageBoom
inactive
minInterval 60
{
   llLogRuleTick("shivajiVillageBoom");
   if (gShivajiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.2;
      btBiasTrade = 0.35;
      cvMinNumVills = 16;
   }
}

//------------------------------------------------------------------------------
// Colonial: Ganimi Kava. Sowar light cavalry raids and Sepoy screen,
// hill-fort built behind them. Forward-base posture activates.
//------------------------------------------------------------------------------
rule shivajiGanimiKava
inactive
minInterval 50
{
   llLogRuleTick("shivajiGanimiKava");
   if (gShivajiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = 0.0;
      btOffenseDefense = 0.65;
      btBiasInf = 0.55;
      btBiasCav = 0.75;            // Sowar / Mahout raid pressure.
      btBiasArt = -0.3;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Fortress: Maratha statecraft. Mahout / Howdah elephants, Mansabdar units,
// Gurkha ridge fire. Hill-fort line locks down ground.
//------------------------------------------------------------------------------
rule shivajiMarathaStatecraft
inactive
minInterval 55
{
   llLogRuleTick("shivajiMarathaStatecraft");
   if (gShivajiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.75;
      btBiasInf = 0.7;
      btBiasCav = 0.85;            // Howdah Elephant + Sowar mass.
      btBiasArt = 0.3;
      cvMaxArmyPop = 130;
      cvMaxTowers = 7;
   }
}

//------------------------------------------------------------------------------
// Industrial: Hill-fort war. Siege Elephant breaks fortified positions;
// Gurkha + Sepoy + Sowar continue. The Maratha Confederacy expands.
//------------------------------------------------------------------------------
rule shivajiHillFortWar
inactive
minInterval 70
{
   llLogRuleTick("shivajiHillFortWar");
   if (gShivajiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 0.85;
      btBiasCav = 0.9;
      btBiasArt = 0.5;
      cvMaxArmyPop = 145;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Maratha host - maximum elephant and cavalry mass with Sepoy
// volley and Siege Elephant park; full Caravanserai trade leaning.
//------------------------------------------------------------------------------
rule shivajiMarathaHost
inactive
minInterval 90
{
   llLogRuleTick("shivajiMarathaHost");
   if (gShivajiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 0.9;
      btBiasCav = 1.0;
      btBiasArt = 0.65;
      btBiasTrade = 0.35;
      cvMaxArmyPop = 160;
   }
}

void enableLeaderShivajiRules(void)
{
   if (gShivajiRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("shivajiVillageBoom");
   xsEnableRule("shivajiGanimiKava");
   xsEnableRule("shivajiMarathaStatecraft");
   xsEnableRule("shivajiHillFortWar");
   xsEnableRule("shivajiMarathaHost");
}
