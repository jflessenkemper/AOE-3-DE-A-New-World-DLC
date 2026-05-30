//==============================================================================
/* leader_tokugawa.xs

   Tokugawa Ieyasu - Edo Bakufu founder personality.

   Historical doctrine:
     - Sekigahara (1600) and Osaka (1614-15): Tokugawa won by patient
       maneuver and political pressure, not by reckless cavalry charges.
       Mapped to a defensive baseline that converts to a methodical
       Fortress timing rather than a Colonial rush.
     - Ashigaru musket lines: Japanese teppou were the dominant arm by the
       Sengoku end. Mapped to a heavy infantry bias once Fortress hits.
     - Shrine economy (Japanese civ unique): wood-tap shrines feed coin
       and food passively. Mapped to the Shrine Trade Node Spread style
       and a strong Trade Route lean.
     - No Native Treaty: Tokugawa closed Japan after 1635 (sakoku). Mapped
       to a deeply negative Native Treaty bias - regulars only.
     - Yumi Bowman + Yabusame screen, Naginata Rider counter-cavalry,
       Flaming Arrow rocket-cart artillery. The standard Edo composition.
*/
//==============================================================================

bool gTokugawaRulesEnabled = false;

void initLeaderTokugawa(void)
{
   llVerboseEcho("A New World: activating Tokugawa Ieyasu personality.");

   llSetDefensivePersonality();
   btRushBoom = -0.4;             // Hard boom; the Bakufu builds first.
   btOffenseDefense = -0.15;      // Defensive baseline.
   btBiasTrade = 0.5;             // Shrine network IS the economy.
   btBiasNative = -0.5;           // Sakoku - closed country.
   llSetMilitaryFocus(0.7, 0.0, 0.3);  // Infantry-led, light cavalry, real artillery.

   // LL-BUILD-STYLE-BEGIN
   llUseShrineTradeNodeSpreadStyle(3);
   gLLEconomicDistanceMultiplier = 1.25;
   // Spec band [1.0, 1.3]. The Shrine/Trade-Node style defaults military
   // to 0.95 (tight muster), which falls just under the band. The Edo
   // Bakufu pushes Ashigaru musket lines and shrine garrisons outward
   // along trade-node corridors — bump military distance slightly so the
   // garrisons reach the shrines they're meant to defend.
   gLLMilitaryDistanceMultiplier = 1.05;
   llSetBuildStrongpointProfile(2, 2, 1, false);
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.85, 0.15, 2, 4.5);

   cvOkToBuildForts = true;
   cvMaxTowers = 6;
   cvMaxArmyPop = 110;

   gTokugawaRulesEnabled = true;
   llLogLeaderState("Tokugawa initialized");
   llProbe("meta.leader_init", "leader=tokugawa");
}

//------------------------------------------------------------------------------
// Discovery: Shrine economy. Settler push and Shrine placement; the
// Bakufu prefers to be patient.
//------------------------------------------------------------------------------
rule tokugawaShrineEconomy
inactive
minInterval 60
{
   llLogRuleTick("tokugawaShrineEconomy");
   if (gTokugawaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.65;
      btBiasTrade = 0.7;
      cvMinNumVills = 18;
   }
}

//------------------------------------------------------------------------------
// Colonial: Yumi screen. Yumi Bowman and Ashigaru musket trickle behind
// shrine and consulate placement. No commitment.
//------------------------------------------------------------------------------
rule tokugawaYumiScreen
inactive
minInterval 50
{
   llLogRuleTick("tokugawaYumiScreen");
   if (gTokugawaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = -0.25;
      btOffenseDefense = 0.0;
      btBiasInf = 0.8;
      btBiasCav = -0.2;
      btBiasArt = -0.3;
      cvMinNumVills = 32;
   }
}

//------------------------------------------------------------------------------
// Fortress: Bakufu Order. Ashigaru musket mass, Samurai shock, Yabusame
// counter-cavalry, Flaming Arrow artillery. The Sengoku army crystallizes.
//------------------------------------------------------------------------------
rule tokugawaBakufuOrder
inactive
minInterval 55
{
   llLogRuleTick("tokugawaBakufuOrder");
   if (gTokugawaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.5;
      btBiasInf = 0.95;
      btBiasCav = 0.3;             // Yabusame and Samurai presence.
      btBiasArt = 0.45;
      btBiasTrade = 0.6;
      cvMaxArmyPop = 130;
      cvMaxTowers = 7;
   }
}

//------------------------------------------------------------------------------
// Industrial: Sengoku consolidation. Kensei elite samurai mass, Ashigaru
// volley, Naginata Rider counter-cavalry, Flaming Arrow at scale.
//------------------------------------------------------------------------------
rule tokugawaSengokuConsolidation
inactive
minInterval 70
{
   llLogRuleTick("tokugawaSengokuConsolidation");
   if (gTokugawaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.7;
      btBiasInf = 1.0;
      btBiasCav = 0.45;
      btBiasArt = 0.65;
      cvMaxArmyPop = 145;
      // Spec expects_treaty=true with no expects_forward: removed llEnableForwardBaseStyle.
      // The Bakufu doctrine consolidates shrines and Edo defenses, not aggressive forward camps.
   }
}

//------------------------------------------------------------------------------
// Imperial: Edo supremacy - maximum Ashigaru / Kensei / Flaming Arrow
// mass with full shrine economy underwriting the war.
//------------------------------------------------------------------------------
rule tokugawaEdoSupremacy
inactive
minInterval 90
{
   llLogRuleTick("tokugawaEdoSupremacy");
   if (gTokugawaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 1.0;
      btBiasCav = 0.5;
      btBiasArt = 0.8;
      btBiasTrade = 0.7;
      cvMaxArmyPop = 160;
   }
}

void enableLeaderTokugawaRules(void)
{
   if (gTokugawaRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("tokugawaShrineEconomy");
   xsEnableRule("tokugawaYumiScreen");
   xsEnableRule("tokugawaBakufuOrder");
   xsEnableRule("tokugawaSengokuConsolidation");
   xsEnableRule("tokugawaEdoSupremacy");
}
