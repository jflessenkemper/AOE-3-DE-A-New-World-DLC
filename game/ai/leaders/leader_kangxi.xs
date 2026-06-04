//==============================================================================
/* leader_kangxi.xs

   Kangxi Emperor (Aisin Gioro Xuanye) - Qing dynasty banner-army personality.

   Historical doctrine:
     - Banner system: Eight Banners cavalry plus Han Green Standard infantry
       provided a layered, mixed-arms imperial army. Mapped to a deliberately
       balanced infantry/cavalry/artillery military focus rather than a
       single-arm push.
     - Pacification campaigns: Three Feudatories (1673-1681), Dzungar campaigns,
       Outer Mongolia integration. Long-running steady wars rather than fast
       gambits. Mapped to a methodical, slightly defensive opener that scales
       into an oppressive Industrial-and-up army.
     - Wonders and consular trade: Forbidden City, Confucian Academy, Porcelain
       Tower; tributary system through Canton. Mapped to wonder-friendly
       behaviour and a measurable trade-route bias.
     - Banner Discipline: every later age widens the army block rather than
       changing its shape. The Qing won by attrition mass, not by surprise.
*/
//==============================================================================

bool gKangxiRulesEnabled = false;

void initLeaderKangxi(void)
{
   anwVerboseEcho("A New World: activating Kangxi Emperor personality.");

   anwSetBalancedPersonality();
   btRushBoom = -0.15;            // Slow, methodical, banner-build first.
   btOffenseDefense = 0.35;       // Mild offense baseline; scales by age.
   btBiasTrade = 0.35;            // Canton trade tributary system.
   btBiasNative = -0.1;           // Tributary kingdoms, not allied villages.
   anwSetMilitaryFocus(0.55, 0.2, 0.35);  // Infantry-heavy, cavalry banner, real artillery.

   // LL-BUILD-STYLE-BEGIN
   anwUseCompactFortifiedCoreStyle(4, true);
   gANWHouseDistanceMultiplier = 0.70;
   gANWMilitaryDistanceMultiplier = 0.85;   // Spec band [0.7,0.9]: tight banner-army deployment.
   anwSetBuildStrongpointProfile(3, 2, 2, false);
   // LL-BUILD-STYLE-END
   anwSetLeaderTacticalDoctrine(0.78, 0.22, 2, 4.0);

   cvOkToBuildForts = true;
   cvMaxTowers = 5;
   cvMaxArmyPop = 115;

   gKangxiRulesEnabled = true;
   anwLogLeaderState("Kangxi initialized");
   anwProbe("meta.leader_init", "leader=kangxi");
}

//------------------------------------------------------------------------------
// Discovery: village boom and explorer scouting. The Qing prefer to know
// the field before committing the bannermen.
//------------------------------------------------------------------------------
rule kangxiVillageBoom
inactive
minInterval 60
{
   anwLogRuleTick("kangxiVillageBoom");
   if (gKangxiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.4;          // Hard boom into Colonial.
      btBiasTrade = 0.5;
      cvMinNumVills = 20;
   }
}

//------------------------------------------------------------------------------
// Colonial: open the banner army. Chu Ko Nu and Changdao infantry blocks
// with Steppe Rider screening. Trade Routes claimed before any commitment
// to early aggression.
//------------------------------------------------------------------------------
rule kangxiBannerOpening
inactive
minInterval 50
{
   anwLogRuleTick("kangxiBannerOpening");
   if (gKangxiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = 0.0;
      btOffenseDefense = 0.4;
      btBiasInf = 0.7;            // Chu Ko Nu / Changdao mass.
      btBiasCav = 0.3;            // Steppe Rider screen.
      btBiasArt = -0.3;           // Save xp for Fortress siege.
      cvMinNumVills = 32;
   }
}

//------------------------------------------------------------------------------
// Fortress: Banner Discipline kicks in. Keshik cavalry, Chu Ko Nu line,
// Flying Crow rocket battery. Forbidden-City forward base.
//------------------------------------------------------------------------------
rule kangxiBannerDiscipline
inactive
minInterval 55
{
   anwLogRuleTick("kangxiBannerDiscipline");
   if (gKangxiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.6;
      btBiasInf = 0.85;
      btBiasCav = 0.4;            // Keshik / Iron Flail wedge.
      btBiasArt = 0.55;           // Flying Crow / Hand Mortar share.
      cvMaxArmyPop = 130;
      anwEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Industrial: pacification campaign tempo. Old Han Army card chains and
// Manchu reserves widen the army block; territory takes precedence over
// daring strikes.
//------------------------------------------------------------------------------
rule kangxiPacificationCampaign
inactive
minInterval 75
{
   anwLogRuleTick("kangxiPacificationCampaign");
   if (gKangxiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.75;
      btBiasInf = 0.95;
      btBiasCav = 0.4;
      btBiasArt = 0.7;
      cvMaxArmyPop = 145;
      cvMaxTowers = 7;
   }
}

//------------------------------------------------------------------------------
// Imperial: full Qing weight. Eight-Banner mass plus Imperial Cannon, broad
// front, methodical advance. Kangxi's late campaigns were never elegant -
// they were unstoppable by virtue of scale.
//------------------------------------------------------------------------------
rule kangxiImperialWeight
inactive
minInterval 90
{
   anwLogRuleTick("kangxiImperialWeight");
   if (gKangxiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 1.0;
      btBiasCav = 0.45;
      btBiasArt = 0.85;
      cvMaxArmyPop = 165;
      anwEnableForwardBaseStyle();
   }
}

void enableLeaderKangxiRules(void)
{
   if (gKangxiRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("kangxiVillageBoom");
   xsEnableRule("kangxiBannerOpening");
   xsEnableRule("kangxiBannerDiscipline");
   xsEnableRule("kangxiPacificationCampaign");
   xsEnableRule("kangxiImperialWeight");
}
