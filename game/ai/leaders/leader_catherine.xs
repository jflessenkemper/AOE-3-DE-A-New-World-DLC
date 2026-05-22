//==============================================================================
/* leader_catherine.xs

   Ivan IV Vasilyevich ("Ivan the Terrible", Tsar 1547-1584) - lobby-matched
   Russian leader. File name kept as "catherine" because the engine personality
   ID is "Catherine" (personalities.xml); function and rule names preserve
   that key for the engine's AI dispatch. All user-visible strings, knobs,
   and portraits have been rebranded to Ivan's doctrine.

   Historical doctrine:
     - Streltsy corps (founded 1550): Ivan institutionalised Russia's first
       permanent musket-armed infantry, the Streltsy, wielding the
       characteristic berdiche axe-rest. Mapped to an extreme infantry mass
       bias and Streltsy-block composition earlier and heavier than
       Catherine's more balanced line.
     - Siege of Kazan (1552) and Astrakhan (1556): Ivan's conquest pattern
       was methodical siege warfare, tall mobile towers, and the reduction
       of fortified Khanate cities. Mapped to early fort commitment,
       higher siege bias than the prior tuning, and patient forward-base
       posture.
     - Oprichnina terror state (1565-1572): Ivan's black-cloaked Oprichnik
       cavalry were a dedicated shock corps whose remit was internal terror
       and frontier raiding. Mapped to a sharper Oprichnik-shock cavalry
       weight, especially at Fortress.
     - Pomestnoye cadre economy: hereditary service-class landlords (Ivan
       formalised the pomestie grant) feed the host. Kept - same Russian
       estate pattern as before, with a slightly more military-leaning
       tilt (Ivan did not run an Enlightenment court).
     - Livonian War (1558-1583): the reign's grinding northwest front.
       Mapped to sustained Imperial-age pressure rather than a burst
       campaign.
*/
//==============================================================================

bool gCatherineRulesEnabled = false;

void initLeaderCatherine(void)
{
   llVerboseEcho("A New World DLC: activating Ivan the Terrible personality.");

   llSetBalancedPersonality();
   btRushBoom = -0.15;            // Slightly earlier army than Catherine's tuning.
   btOffenseDefense = 0.55;       // More openly offensive - Ivan was a conqueror, not an administrator.
   btBiasTrade = 0.2;             // Less mercantile than Catherine; war pays for war.
   btBiasNative = 0.05;           // Sparse - Ivan absorbed Tatar Khanates by sword, not treaty.
   llSetMilitaryFocus(0.9, 0.45, 0.45);  // Streltsy mass + Oprichnik shock + siege train.

   // LL-BUILD-STYLE-BEGIN
   llUseCossackVoiskoStyle(1);
   // Spec override: Russians Catherine doctrine — see playstyle_spec.json
   gLLWallStrategy = cLLWallStrategyFrontierPalisades;
   llSetBuildStrongpointProfile(2, 2, 3, true);
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.78, 0.22, 2, 4.0);

   cvOkToBuildForts = true;
   cvMaxTowers = 5;
   cvMaxArmyPop = 130;            // Russian mass.

   gCatherineRulesEnabled = true;
   llLogLeaderState("Ivan the Terrible initialized");
   llProbe("meta.leader_init", "leader=catherine");
}

//------------------------------------------------------------------------------
// Discovery: Pomestnoye boom. Settler push and Trade Post placement;
// the gentry organize the rural economy.
//------------------------------------------------------------------------------
rule catherinePomestnoyeBoom
inactive
minInterval 60
{
   llLogRuleTick("catherinePomestnoyeBoom");
   if (gCatherineRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.4;
      btBiasTrade = 0.45;
      cvMinNumVills = 18;
   }
}

//------------------------------------------------------------------------------
// Colonial: Streltsy block. Streltsy musket mass and Cossack screen,
// forward base posture; the army assembles in depth.
//------------------------------------------------------------------------------
rule catherineStreltsyBlock
inactive
minInterval 50
{
   llLogRuleTick("catherineStreltsyBlock");
   if (gCatherineRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = -0.05;
      btOffenseDefense = 0.5;
      btBiasInf = 0.95;            // Block infantry mass.
      btBiasCav = 0.4;             // Cossack hetmans.
      btBiasArt = -0.1;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Fortress: Imperial Expansion. Musketeer line, Oprichnik shock, Cossack
// flank, Falconet support. Suvorov-style combined-arms columns.
//------------------------------------------------------------------------------
rule catherineImperialExpansion
inactive
minInterval 55
{
   llLogRuleTick("catherineImperialExpansion");
   if (gCatherineRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.7;
      btBiasInf = 1.0;
      btBiasCav = 0.55;
      btBiasArt = 0.5;
      cvMaxArmyPop = 145;
   }
}

//------------------------------------------------------------------------------
// Industrial: Russo-Turkish campaign. Heavy Cannon park, Musketeer mass,
// Cossack and Oprichnik mounted reserve. The empire crushes by depth.
//------------------------------------------------------------------------------
rule catherineRussoTurkishCampaign
inactive
minInterval 70
{
   llLogRuleTick("catherineRussoTurkishCampaign");
   if (gCatherineRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 1.0;
      btBiasCav = 0.65;
      btBiasArt = 0.7;
      cvMaxArmyPop = 160;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Romanov supremacy - maximum Musketeer / Strelet / Heavy Cannon
// mass with continuous Cossack pressure on the wings.
//------------------------------------------------------------------------------
rule catherineRomanovSupremacy
inactive
minInterval 90
{
   llLogRuleTick("catherineRomanovSupremacy");
   if (gCatherineRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 1.0;
      btBiasCav = 0.7;
      btBiasArt = 0.85;
      cvMaxArmyPop = 175;
   }
}

void enableLeaderCatherineRules(void)
{
   if (gCatherineRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("catherinePomestnoyeBoom");
   xsEnableRule("catherineStreltsyBlock");
   xsEnableRule("catherineImperialExpansion");
   xsEnableRule("catherineRussoTurkishCampaign");
   xsEnableRule("catherineRomanovSupremacy");
}
