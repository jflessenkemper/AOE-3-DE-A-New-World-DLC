//==============================================================================
/* leader_garibaldi.xs

   Giuseppe Garibaldi - Risorgimento volunteer-army personality.

   Historical doctrine:
     - Camicie Rosse (Redshirts): irregular volunteer columns that won
       campaigns through speed, audacity, and political momentum rather
       than parade-ground drill. Mapped to a forward, fast-committing
       Colonial push and a meaningful skirmisher / bersaglieri bias.
     - Expedition of the Thousand (1860): Garibaldi landed 1,000 men in
       Sicily and toppled the Bourbon Two Sicilies. Mapped to an
       aggressive Colonial timing supported by Forward Operational Line
       build style.
     - Bersaglieri light infantry: Italian elite skirmishers known for
       running cadence and rifle work. The Bersagliere elite designation
       matches; mapped to a strong infantry bias from Fortress.
     - Pavisier shield-shot tradition (Italian civ unique): heavy crossbow
       supported by tower shields. Maps to a real defensive backbone behind
       the skirmisher line.
     - Basilica + Lombard economy: Italian civ produces XP from Basilicas
       and a strong shipment cycle. Mapped to a moderate Trade Route lean.
*/
//==============================================================================

bool gGaribaldiRulesEnabled = false;

void initLeaderGaribaldi(void)
{
   llVerboseEcho("A New World: activating Giuseppe Garibaldi personality.");

   llSetAggressivePersonality();
   btRushBoom = 0.05;             // Light boom; the campaign opens early.
   btOffenseDefense = 0.6;
   btBiasTrade = 0.2;
   btBiasNative = 0.0;
   llSetMilitaryFocus(0.65, 0.35, 0.25);

   // LL-BUILD-STYLE-BEGIN
   // earlyWalls=true honours spec first_wall_before_ms=900000 (Levee default
   // is false for revolutionary mobile civs; Garibaldi runs static-base levee).
   llUseRepublicanLeveeStyle(2, true);
   gLLMilitaryDistanceMultiplier = 0.90;
   llSetBuildStrongpointProfile(2, 2, 3, true);
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);

   cvOkToBuildForts = true;
   cvMaxTowers = 4;
   cvMaxArmyPop = 115;

   gGaribaldiRulesEnabled = true;
   llLogLeaderState("Garibaldi initialized");
   llProbe("meta.leader_init", "leader=garibaldi");
}

//------------------------------------------------------------------------------
// Discovery: Risorgimento boom. Settler push and Basilica placement; the
// volunteer army comes when the politics permits.
//------------------------------------------------------------------------------
rule garibaldiRisorgimentoBoom
inactive
minInterval 60
{
   llLogRuleTick("garibaldiRisorgimentoBoom");
   if (gGaribaldiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.15;
      btBiasTrade = 0.3;
      cvMinNumVills = 16;
   }
}

//------------------------------------------------------------------------------
// Colonial: Camicie Rosse. Schiavone and Crossbowman screen, Pavisier
// commitment when the army crystallizes. Forward operational line opens.
//------------------------------------------------------------------------------
rule garibaldiCamicieRosse
inactive
minInterval 50
{
   llLogRuleTick("garibaldiCamicieRosse");
   if (gGaribaldiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasInf = 0.85;            // Pavisier + Crossbow mass.
      btBiasCav = 0.25;
      btBiasArt = -0.2;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Fortress: Volunteer Columns. Bersagliere skirmish line, Schiavone shock,
// Pavisier shield wall, Falconet support. The Risorgimento takes the field.
//------------------------------------------------------------------------------
rule garibaldiVolunteerColumns
inactive
minInterval 55
{
   llLogRuleTick("garibaldiVolunteerColumns");
   if (gGaribaldiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.8;
      btBiasInf = 0.95;
      btBiasCav = 0.45;            // Schiavone shock cavalry.
      btBiasArt = 0.4;
      cvMaxArmyPop = 130;
   }
}

//------------------------------------------------------------------------------
// Industrial: Expedition of the Thousand at scale. Bersagliere mass,
// Heavy Cannon park, Schiavone reserve. Italy on the march.
//------------------------------------------------------------------------------
rule garibaldiThousandMarch
inactive
minInterval 70
{
   llLogRuleTick("garibaldiThousandMarch");
   if (gGaribaldiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 1.0;
      btBiasCav = 0.5;
      btBiasArt = 0.6;
      cvMaxArmyPop = 145;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Italian Unification. Maximum Bersagliere / Pavisier / Heavy
// Cannon mass with Schiavone wing; trade lines fully invested.
//------------------------------------------------------------------------------
rule garibaldiUnificationHost
inactive
minInterval 90
{
   llLogRuleTick("garibaldiUnificationHost");
   if (gGaribaldiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 1.0;
      btBiasCav = 0.55;
      btBiasArt = 0.75;
      btBiasTrade = 0.35;
      cvMaxArmyPop = 160;
   }
}

void enableLeaderGaribaldiRules(void)
{
   if (gGaribaldiRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("garibaldiRisorgimentoBoom");
   xsEnableRule("garibaldiCamicieRosse");
   xsEnableRule("garibaldiVolunteerColumns");
   xsEnableRule("garibaldiThousandMarch");
   xsEnableRule("garibaldiUnificationHost");
}
