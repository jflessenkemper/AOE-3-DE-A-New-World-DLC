//==============================================================================
/* leader_crazy_horse.xs

   Phizí ("Chief Gall", Hunkpapa Lakota war chief, c. 1840-1894) - lobby-matched
   Lakota leader. File name kept as "crazy_horse" because the engine personality
   ID is "Crazyhorse" (personalities.xml); function and rule names preserve
   that key for the engine's AI dispatch. All user-visible strings have been
   rebranded to Gall's doctrine.

   Historical doctrine:
     - Little Bighorn envelopment (June 25, 1876): Gall led the initial
       Hunkpapa charge that broke Reno's line at the south end of the
       Lakota camp, then wheeled north with Crow King and Iron Horn to
       envelop Custer's detachment on Calhoun Hill. Mapped to a very
       aggressive offensive baseline and forward commitment from Colonial
       on, reflecting a coordinated mass-cavalry envelopment rather than
       an individual-valor charge.
     - Plains cavalry wedge: Lakota war bands fought as horse archers and
       lance cavalry - Wakina Rifle Rider, Cetan Bowman, Axe Rider,
       Tashunke Prowler. Mapped to a near-pure cavalry composition with
       almost no static infantry weight and no artillery.
     - Buffalo economy: Lakota civ trades static structures for tipi
       mobility and Buffalo hunts. Mobile Frontier Scatter build style and
       a very negative Trade Route lean.
     - Hunkpapa confederation: Sitting Bull's Hunkpapa, plus Oglala,
       Cheyenne, Arapaho, and Dakota allies. Strong Native Treaty bias.
     - No fortress doctrine, no artillery - Lakota warfare is fast, mobile,
       and decisive at the point of envelopment.
*/
//==============================================================================

bool gCrazyHorseRulesEnabled = false;

void initLeaderCrazyHorse(void)
{
   anwVerboseEcho("A New World DLC: activating Chief Gall personality.");

   anwSetAggressivePersonality();
   btRushBoom = 0.4;              // Almost no boom; the warpath opens immediately.
   btOffenseDefense = 0.85;       // Maximum offensive lean of any standard nation.
   btBiasTrade = -0.55;
   btBiasNative = 0.55;
   anwSetMilitaryFocus(0.15, 0.85, -0.3);  // Cavalry totem.

   // LL-BUILD-STYLE-BEGIN
   anwUseSteppeCavalryWedgeStyle(0);
   gANWMilitaryDistanceMultiplier = 1.15;   // Spec band [1.1,1.3]: forward cavalry envelopment.
   // LL-BUILD-STYLE-END
   anwSetLeaderTacticalDoctrine(0.55, 0.45, 2, 2.5);

   cvOkToBuildForts = false;      // Lakota do not turtle.
   cvMaxTowers = 2;
   cvMaxArmyPop = 110;

   gCrazyHorseRulesEnabled = true;
   anwLogLeaderState("Chief Gall initialized");
   anwProbe("meta.leader_init", "leader=crazyhorse");
}

//------------------------------------------------------------------------------
// Discovery: Buffalo camp. Tipi sprawl, native trade post; the war
// council assembles immediately after.
//------------------------------------------------------------------------------
rule crazyHorseBuffaloCamp
inactive
minInterval 55
{
   anwLogRuleTick("crazyHorseBuffaloCamp");
   if (gCrazyHorseRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = 0.1;
      btBiasNative = 0.7;
      cvMinNumVills = 14;
   }
}

//------------------------------------------------------------------------------
// Colonial: Running fight. Axe Rider and Cetan Bowman pressure on enemy
// villager and trade lines from Colonial onward.
//------------------------------------------------------------------------------
rule crazyHorseRunningFight
inactive
minInterval 45
{
   anwLogRuleTick("crazyHorseRunningFight");
   if (gCrazyHorseRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = 0.15;
      btOffenseDefense = 0.9;
      btBiasInf = 0.0;
      btBiasCav = 0.95;            // Axe Rider and Cetan as the hammer.
      btBiasArt = -0.6;
      anwEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Fortress: Wakina horse archers. Wakina Rifle Riders and Tashunke Prowler
// mass form the field army; Dog Soldier shock arm.
//------------------------------------------------------------------------------
rule crazyHorseWakinaWar
inactive
minInterval 50
{
   anwLogRuleTick("crazyHorseWakinaWar");
   if (gCrazyHorseRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 0.1;
      btBiasCav = 1.0;
      btBiasArt = -0.5;
      cvMaxArmyPop = 125;
   }
}

//------------------------------------------------------------------------------
// Industrial: Bighorn war. Maximum Wakina / Tashunke / Axe Rider mass.
// Native treaty pulled to the limit. The plains burn.
//------------------------------------------------------------------------------
rule crazyHorseBighornWar
inactive
minInterval 65
{
   anwLogRuleTick("crazyHorseBighornWar");
   if (gCrazyHorseRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 1.0;
      btBiasInf = 0.15;
      btBiasCav = 1.0;
      btBiasArt = -0.4;
      btBiasNative = 0.7;
      cvMaxArmyPop = 140;
      anwEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Lakota host - all cavalry, all native, no quarter. The
// largest possible mounted host the engine will field.
//------------------------------------------------------------------------------
rule crazyHorseLakotaHost
inactive
minInterval 80
{
   anwLogRuleTick("crazyHorseLakotaHost");
   if (gCrazyHorseRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 1.0;
      btBiasInf = 0.2;
      btBiasCav = 1.0;
      btBiasArt = -0.2;
      btBiasNative = 0.8;
      cvMaxArmyPop = 155;
   }
}

void enableLeaderCrazyHorseRules(void)
{
   if (gCrazyHorseRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("crazyHorseBuffaloCamp");
   xsEnableRule("crazyHorseRunningFight");
   xsEnableRule("crazyHorseWakinaWar");
   xsEnableRule("crazyHorseBighornWar");
   xsEnableRule("crazyHorseLakotaHost");
}
