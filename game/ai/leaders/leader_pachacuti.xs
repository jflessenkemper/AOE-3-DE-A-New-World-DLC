//==============================================================================
/* leader_pachacuti.xs

   Pachacuti (Pachakutiq Inka Yupanki) - Inca empire-builder personality.

   Historical doctrine:
     - Tawantinsuyu expansion: Pachacuti turned a regional kingdom into the
       largest empire in the pre-Columbian Americas. Mapped to a slow,
       methodical opening that snowballs into mass infantry by Fortress.
     - Mit'a labor and qhapaq nan road network: every conquered valley owed
       service and was bound to the imperial road. Mapped to the Mobile
       Frontier Scatter style and a Native Treaty leaning - Quechua, Aymara,
       and Chimu drafts feed the army.
     - Andean fortress warfare: Sacsayhuaman, Ollantaytambo, Pisac. Mapped
       to high tower count, fort-friendly behavior, and a defensive baseline
       in the early ages.
     - Bolas / Maceman / Spearman composition: no horse, no cannon - mass
       infantry of varied close-quarters and ranged roles. Mapped to a
       dominant infantry bias and near-zero cavalry weight.
     - Jungle Bowman and Huaraca slingers: ranged screening in front of
       the maceman block. Standard Inca line.
*/
//==============================================================================

bool gPachacutiRulesEnabled = false;

void initLeaderPachacuti(void)
{
   llVerboseEcho("A New World: activating Pachacuti personality.");

   llSetDefensivePersonality();
   btRushBoom = -0.3;             // Hard boom - Mit'a economy first.
   btOffenseDefense = -0.1;
   btBiasTrade = -0.1;
   btBiasNative = 0.45;           // Quechua / Aymara / Chimu drafts.
   llSetMilitaryFocus(0.85, -0.3, 0.1);  // Infantry-only doctrine.

   // LL-BUILD-STYLE-BEGIN
   llUseAndeanTerraceFortressStyle(4);
   gLLHouseDistanceMultiplier = 0.75;
   gLLMilitaryDistanceMultiplier = 0.80;  // Sacsayhuamán-tight concentric fortress — mid-band of spec [0.7,1.0]; barracks ring inside the wall belt, not at the ceiling.
   llSetBuildStrongpointProfile(3, 3, 2, false);
   // Spec override: Inca Pachacuti doctrine — Sacsayhuamán concentric
   // ring fortress (Tier-walls the high ground in two or three concentric
   // rings — see playstyle_spec.json "Inca Pachacuti".doctrine_prose).
   // Andean Terrace helper defaults to ChokepointSegments(1); override
   // to FortressRing(0) to match the spec.
   gLLWallStrategy = cLLWallStrategyFortressRing;
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.82, 0.18, 2, 4.5);

   cvOkToBuildForts = true;
   cvMaxTowers = 7;               // Andean fortress emphasis.
   cvMaxArmyPop = 115;

   gPachacutiRulesEnabled = true;
   llLogLeaderState("Pachacuti initialized");
   llProbe("meta.leader_init", "leader=pachacuti");
}

//------------------------------------------------------------------------------
// Discovery: Mit'a economy. Settler push and Native Trade Posts; the army
// waits for the road network to open.
//------------------------------------------------------------------------------
rule pachacutiMitaEconomy
inactive
minInterval 60
{
   llLogRuleTick("pachacutiMitaEconomy");
   if (gPachacutiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.55;
      btBiasNative = 0.6;
      cvMinNumVills = 18;
   }
}

//------------------------------------------------------------------------------
// Colonial: Bolas screen. Bolas Warrior + Huaraca slinger pressure on
// villager lines, Spearmen anchor. No artillery, no cavalry.
//------------------------------------------------------------------------------
rule pachacutiBolasScreen
inactive
minInterval 50
{
   llLogRuleTick("pachacutiBolasScreen");
   if (gPachacutiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = -0.1;
      btOffenseDefense = 0.2;
      btBiasInf = 0.85;
      btBiasCav = -0.5;
      btBiasArt = -0.5;
      cvMinNumVills = 30;
   }
}

//------------------------------------------------------------------------------
// Fortress: Mountain Empire. Maceman block, Jungle Bowman ranged screen,
// fort-anchored push. The Andean army takes its shape.
//------------------------------------------------------------------------------
rule pachacutiMountainEmpire
inactive
minInterval 55
{
   llLogRuleTick("pachacutiMountainEmpire");
   if (gPachacutiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.55;
      btBiasInf = 1.0;
      btBiasCav = -0.4;
      btBiasArt = -0.2;
      cvMaxArmyPop = 130;
      cvMaxTowers = 8;
   }
}

//------------------------------------------------------------------------------
// Industrial: Tawantinsuyu war. Maceman / Bolas / Jungle Bowman mass
// continues; some captured artillery (Light Cannon) finally appears via
// natives. The empire pushes outward.
//------------------------------------------------------------------------------
rule pachacutiTawantinsuyuWar
inactive
minInterval 70
{
   llLogRuleTick("pachacutiTawantinsuyuWar");
   if (gPachacutiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.7;
      btBiasInf = 1.0;
      btBiasCav = -0.3;
      btBiasArt = 0.1;
      cvMaxArmyPop = 145;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Sapa Inca host. Maximum infantry mass, fortified cordon,
// Native Treaty drafts at full tilt.
//------------------------------------------------------------------------------
rule pachacutiSapaIncaHost
inactive
minInterval 90
{
   llLogRuleTick("pachacutiSapaIncaHost");
   if (gPachacutiRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 1.0;
      btBiasCav = -0.2;
      btBiasArt = 0.25;
      btBiasNative = 0.7;
      cvMaxArmyPop = 160;
   }
}

void enableLeaderPachacutiRules(void)
{
   if (gPachacutiRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("pachacutiMitaEconomy");
   xsEnableRule("pachacutiBolasScreen");
   xsEnableRule("pachacutiMountainEmpire");
   xsEnableRule("pachacutiTawantinsuyuWar");
   xsEnableRule("pachacutiSapaIncaHost");
}
