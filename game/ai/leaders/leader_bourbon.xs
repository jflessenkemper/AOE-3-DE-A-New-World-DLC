//==============================================================================
/* leader_bourbon.xs

   Louis XVIII (Louis-Stanislas-Xavier de France) - Bourbon Restoration
   personality. The deliberate counterpoint to the Napoleonic France
   commander: cautious, traditionalist, fortification-and-court rather
   than artillery-and-momentum.

   Historical doctrine:
     - Restoration cabinet army: post-1815 royal army was professional but
       small, leaning on Maison du Roi household cavalry, gendarmes, and
       traditional line regiments rather than Napoleonic mass-conscript
       columns. Mapped to a balanced infantry/cavalry mix with restrained
       artillery.
     - Trade and reconciliation: Talleyrand-style trade diplomacy, white
       flag commerce restored. Mapped to a heavy Trade Route bias and a
       conscious refusal of native treaties (Bourbon traditionalism).
     - Court and chateau economy: Versailles-style fortification of the
       interior, Marshal forts on the frontier. Build style is Compact
       Fortified Core, very fort-friendly.
     - Cuirassier shock reserve: Bourbon doctrine kept heavy household
       cavalry as a counter-charge reserve, never a first-wave hammer.
       Mapped to defensive posture with cavalry available later, not now.
     - Skirmisher tradition (Voltigeurs): elite light infantry screen on
       the wings - the Skirmisher elite designation matches.
*/
//==============================================================================

bool gBourbonRulesEnabled = false;

void initLeaderBourbon(void)
{
   anwVerboseEcho("A New World: activating Louis XVIII personality.");

   anwSetDefensivePersonality();
   btRushBoom = -0.45;            // Heavy boom; restored economy first.
   btOffenseDefense = -0.3;       // Defensive baseline.
   btBiasTrade = 0.55;            // White-flag commerce.
   btBiasNative = -0.4;           // Bourbon traditionalism: regulars only.
   anwSetMilitaryFocus(0.55, 0.35, 0.2);  // Balanced inf/cav, restrained art.

   // LL-BUILD-STYLE-BEGIN
   anwUseCompactFortifiedCoreStyle(3, true);
   gANWEconomicDistanceMultiplier = 1.05;
   gANWMilitaryDistanceMultiplier = 0.85;   // Spec band [0.7,0.9]: Restoration interior fort line.
   anwSetBuildStrongpointProfile(3, 2, 2, false);
   // LL-BUILD-STYLE-END
   anwSetLeaderTacticalDoctrine(0.88, 0.12, 2, 5.0);  // Royal explorer well behind the line.

   cvOkToBuildForts = true;
   cvMaxTowers = 6;
   cvMaxArmyPop = 110;
   cvDefenseReflexRadiusActive = 72.0;
   cvDefenseReflexSearchRadius = 72.0;
   cvDefenseReflexRadiusPassive = 30.0;

   gBourbonRulesEnabled = true;
   anwLogLeaderState("Bourbon initialized");
   anwProbe("meta.leader_init", "leader=bourbon");
}

//------------------------------------------------------------------------------
// Discovery: court economy. Trade Routes, Settler push, no army.
//------------------------------------------------------------------------------
rule bourbonCourtEconomy
inactive
minInterval 60
{
   anwLogRuleTick("bourbonCourtEconomy");
   if (gBourbonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.7;
      btBiasTrade = 0.7;
      cvMinNumVills = 18;
   }
}

//------------------------------------------------------------------------------
// Colonial: chateau line. Skirmisher screen and a Musketeer trickle. No
// commitment to forward action; build banks and forts of the interior.
//------------------------------------------------------------------------------
rule bourbonChateauLine
inactive
minInterval 50
{
   anwLogRuleTick("bourbonChateauLine");
   if (gBourbonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = -0.3;
      btOffenseDefense = -0.1;
      btBiasInf = 0.7;
      btBiasCav = 0.05;
      btBiasArt = -0.3;
      cvMinNumVills = 32;
   }
}

//------------------------------------------------------------------------------
// Fortress: Maison du Roi. The Cuirassier shock reserve assembles, line
// infantry mass forms behind a fort line, Voltigeur skirmishers on the
// wings. Defensive posture remains.
//------------------------------------------------------------------------------
rule bourbonRoyalArmy
inactive
minInterval 55
{
   anwLogRuleTick("bourbonRoyalArmy");
   if (gBourbonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.05;
      btBiasInf = 0.85;
      btBiasCav = 0.55;            // Cuirassier shock reserve.
      btBiasArt = 0.3;
      btBiasTrade = 0.65;
      cvMaxArmyPop = 125;
   }
}

//------------------------------------------------------------------------------
// Industrial: Restoration front. Maison du Roi cavalry counter-charge,
// Heavy Cannon support, fort line creeps forward. Still a slow,
// court-paced campaign.
//------------------------------------------------------------------------------
rule bourbonRestorationFront
inactive
minInterval 80
{
   anwLogRuleTick("bourbonRestorationFront");
   if (gBourbonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.25;
      btBiasInf = 0.95;
      btBiasCav = 0.55;
      btBiasArt = 0.55;
      cvMaxArmyPop = 140;
      cvMaxTowers = 8;
      anwEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Restoration consolidation. Heavy Cannon park, Maison du Roi
// reserve, fort-anchored advance. Bourbon France never marches like
// Napoleon - it sits down on the ground it owns and forces you off.
//------------------------------------------------------------------------------
rule bourbonRestorationGuard
inactive
minInterval 90
{
   anwLogRuleTick("bourbonRestorationGuard");
   if (gBourbonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.45;
      btBiasInf = 1.0;
      btBiasCav = 0.6;
      btBiasArt = 0.7;
      cvMaxArmyPop = 155;
   }
}

void enableLeaderBourbonRules(void)
{
   if (gBourbonRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("bourbonCourtEconomy");
   xsEnableRule("bourbonChateauLine");
   xsEnableRule("bourbonRoyalArmy");
   xsEnableRule("bourbonRestorationFront");
   xsEnableRule("bourbonRestorationGuard");
}
