//==============================================================================
/* leader_menelik.xs

   Menelik II of Ethiopia - Solomonic dynasty modernization personality.

   Historical doctrine:
     - Highland mobilization: Shewan and Oromo levies brought as mass infantry,
       organized in regional regiments (Oromo Warriors, Shotel Warriors,
       Gascenya, Neftenya). Mapped to a deep, infantry-led army with strong
       native-treaty leaning.
     - Imported modernization: Menelik bought tens of thousands of European
       rifles and a real artillery park before Adwa. Mapped to a measurable
       artillery share once Fortress hits, especially at Industrial.
     - Adwa doctrine (1896): infantry mass at the centre, light cavalry on
       the flanks (Javelin Riders), artillery cracking columns from the
       ridge line. Mapped to forward-base aggressiveness from Fortress on.
     - Imperial cohesion: Menelik bound rival lords by marriage, tribute,
       and shared campaign. Mapped to a genuine native-trade leaning rather
       than the European-style trade-route obsession.
     - Highland geography: Ethiopia fights from elevation. Build style is
       Compact Fortified Core, fort-anchored.
*/
//==============================================================================

bool gMenelikRulesEnabled = false;

void initLeaderMenelik(void)
{
   llVerboseEcho("A New World: activating Menelik II personality.");

   llSetAggressivePersonality();
   btRushBoom = 0.15;             // Mild boom, then commit.
   btOffenseDefense = 0.55;
   btBiasTrade = 0.15;
   btBiasNative = 0.5;            // Oromo, Tigrayan, Afar levies.
   llSetMilitaryFocus(0.7, 0.05, 0.35);

   // LL-BUILD-STYLE-BEGIN
   llUseHighlandCitadelStyle(3);
   gLLHouseDistanceMultiplier = 0.80;
   gLLMilitaryDistanceMultiplier = 0.85;  // Defensive highland citadel — mid-band of spec [0.7,1.0]; barracks/stables tuck back from front, not at the very ceiling.
   llSetBuildStrongpointProfile(3, 2, 2, false);
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.78, 0.22, 2, 4.0);

   cvOkToBuildForts = true;
   cvMaxTowers = 5;
   cvMaxArmyPop = 120;            // Highland levies are numerous.

   gMenelikRulesEnabled = true;
   llLogLeaderState("Menelik initialized");
   llProbe("meta.leader_init", "leader=menelik");
}

//------------------------------------------------------------------------------
// Discovery: highland levy boom. Native Trade Posts first.
//------------------------------------------------------------------------------
rule menelikHighlandLevy
inactive
minInterval 60
{
   llLogRuleTick("menelikHighlandLevy");
   if (gMenelikRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.1;
      btBiasNative = 0.7;
      cvMinNumVills = 18;
   }
}

//------------------------------------------------------------------------------
// Colonial: warband pressure. Oromo Warrior and Shotel Warrior pressure on
// villager and trade lines, supported by light Javelin Rider screen.
//------------------------------------------------------------------------------
rule menelikWarbandPressure
inactive
minInterval 50
{
   llLogRuleTick("menelikWarbandPressure");
   if (gMenelikRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = 0.0;
      btOffenseDefense = 0.65;
      btBiasInf = 0.95;
      btBiasCav = 0.25;            // Javelin Riders for chase.
      btBiasArt = -0.4;            // Save xp for Fortress imports.
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Fortress: highland modernization. European rifles arrive (Gascenya /
// Neftenya), mortars buy ridge dominance.
//------------------------------------------------------------------------------
rule menelikHighlandModernization
inactive
minInterval 55
{
   llLogRuleTick("menelikHighlandModernization");
   if (gMenelikRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.75;
      btBiasInf = 1.0;
      btBiasCav = 0.25;
      btBiasArt = 0.6;             // Mortar / cannon imports.
      cvMaxArmyPop = 135;
   }
}

//------------------------------------------------------------------------------
// Industrial: Adwa-style assault posture. Mass infantry block, mortar park,
// light cavalry sweeping enemy artillery.
//------------------------------------------------------------------------------
rule menelikAdwaPosture
inactive
minInterval 70
{
   llLogRuleTick("menelikAdwaPosture");
   if (gMenelikRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 1.0;
      btBiasCav = 0.3;
      btBiasArt = 0.75;
      cvMaxArmyPop = 150;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: full Solomonic war footing - largest possible infantry mass,
// continuous mortar fire, Oromo cavalry sweeping the flanks.
//------------------------------------------------------------------------------
rule menelikSolomonicWar
inactive
minInterval 90
{
   llLogRuleTick("menelikSolomonicWar");
   if (gMenelikRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 1.0;
      btBiasCav = 0.35;
      btBiasArt = 0.85;
      btBiasNative = 0.7;
      cvMaxArmyPop = 165;
   }
}

void enableLeaderMenelikRules(void)
{
   if (gMenelikRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("menelikHighlandLevy");
   xsEnableRule("menelikWarbandPressure");
   xsEnableRule("menelikHighlandModernization");
   xsEnableRule("menelikAdwaPosture");
   xsEnableRule("menelikSolomonicWar");
}
