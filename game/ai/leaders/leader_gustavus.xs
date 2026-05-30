//==============================================================================
/* leader_gustavus.xs

   Gustav II Adolf - Gustavus Adolphus, "Lion of the North", father of
   modern combined-arms warfare personality.

   Historical doctrine:
     - Mobile artillery doctrine (Breitenfeld 1631, Lutzen 1632): Gustavus
       integrated light regimental cannons directly into the line of
       battle. Mapped to a strong artillery weight from Fortress on, with
       the Leather Cannon (Swedish civ unique) as the centerpiece.
     - Caroline thin-line infantry: small, fast-volleying companies that
       fired by half-rank and counter-marched. Mapped to a deep infantry
       bias and a forward-base posture from Colonial.
     - Hakkapeliitta cavalry (Finnish light horse under Swedish service):
       fast wing cavalry that broke enemy lines after the volley. Mapped
       to a real cavalry share that supports rather than leads.
     - Torps and Sami trade: Swedish civ uses Torps (passive resource
       buildings) and a Native-friendly far-north economy. Mapped to a
       moderate Trade Route lean with mild Native Treaty.
     - Thirty Years' War expeditionary tempo: Sweden fought far from
       home. Mapped to the Forward Operational Line build style.
*/
//==============================================================================

bool gGustavusRulesEnabled = false;

void initLeaderGustavus(void)
{
   llVerboseEcho("A New World: activating Gustavus Adolphus personality.");

   llSetAggressivePersonality();
   btRushBoom = 0.05;             // Light boom; the campaign opens early.
   btOffenseDefense = 0.65;
   btBiasTrade = 0.25;
   btBiasNative = 0.1;
   llSetMilitaryFocus(0.7, 0.4, 0.6);  // Infantry-led, real cavalry, very real artillery.

   // LL-BUILD-STYLE-BEGIN
   // Spec doctrine = Forward Operational Line. Gustavus pushed forward
   // operating bases ("Lion of the North"), so the Forward helper fits
   // better than the static Siege Train doctrine.
   // Note: gLLMilitaryDistanceMultiplier is set authoritatively in
   // leaderCommon.xs llApplyBuildStyleForActiveCiv (cCivDESwedish → 0.85,
   // mid-band of spec [0.8, 1.1]). Do NOT set it here — the override would
   // be silently clobbered after this init runs, which is misleading.
   llUseForwardOperationalLineStyle(1);
   llSetBuildStrongpointProfile(2, 2, 3, true);
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.74, 0.26, 2, 4.0);

   cvOkToBuildForts = true;
   cvMaxTowers = 4;
   cvMaxArmyPop = 115;

   gGustavusRulesEnabled = true;
   llLogLeaderState("Gustavus initialized");
   llProbe("meta.leader_init", "leader=gustav");
}

//------------------------------------------------------------------------------
// Discovery: Torp boom. Settler push and Torp placement; the army comes
// from a fast economic ramp.
//------------------------------------------------------------------------------
rule gustavusTorpBoom
inactive
minInterval 60
{
   llLogRuleTick("gustavusTorpBoom");
   if (gGustavusRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.15;
      btBiasTrade = 0.4;
      cvMinNumVills = 16;
   }
}

//------------------------------------------------------------------------------
// Colonial: Caroline line. Pikeman + Carolean musket commitment with
// Hakkapeliitta light cavalry on the wings. Forward base posture.
//------------------------------------------------------------------------------
rule gustavusCarolineLine
inactive
minInterval 50
{
   llLogRuleTick("gustavusCarolineLine");
   if (gGustavusRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasInf = 0.85;
      btBiasCav = 0.45;
      btBiasArt = 0.15;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Fortress: Mobile Artillery. Leather Cannon enters the line, Carolean
// musket mass, Hakkapeliitta wing. The Breitenfeld signature.
//------------------------------------------------------------------------------
rule gustavusMobileArtillery
inactive
minInterval 55
{
   llLogRuleTick("gustavusMobileArtillery");
   if (gGustavusRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.8;
      btBiasInf = 0.95;
      btBiasCav = 0.55;
      btBiasArt = 0.75;            // Leather Cannon as line element.
      cvMaxArmyPop = 130;
   }
}

//------------------------------------------------------------------------------
// Industrial: Lutzen Doctrine. Heavy Cannon park, continuous Leather
// Cannon mobility, Carolean mass; Hakkapeliitta sweeps the flanks.
//------------------------------------------------------------------------------
rule gustavusLutzenDoctrine
inactive
minInterval 70
{
   llLogRuleTick("gustavusLutzenDoctrine");
   if (gGustavusRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 1.0;
      btBiasCav = 0.65;
      btBiasArt = 0.85;
      cvMaxArmyPop = 145;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Lion of the North supremacy - maximum Carolean / Leather
// Cannon / Heavy Cannon mass with continuous Hakkapeliitta sweeps.
//------------------------------------------------------------------------------
rule gustavusLionOfTheNorth
inactive
minInterval 90
{
   llLogRuleTick("gustavusLionOfTheNorth");
   if (gGustavusRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 1.0;
      btBiasCav = 0.7;
      btBiasArt = 1.0;
      cvMaxArmyPop = 160;
   }
}

void enableLeaderGustavusRules(void)
{
   if (gGustavusRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("gustavusTorpBoom");
   xsEnableRule("gustavusCarolineLine");
   xsEnableRule("gustavusMobileArtillery");
   xsEnableRule("gustavusLutzenDoctrine");
   xsEnableRule("gustavusLionOfTheNorth");
}
