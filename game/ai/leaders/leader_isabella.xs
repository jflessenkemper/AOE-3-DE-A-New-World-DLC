//==============================================================================
/* leader_isabella.xs

   Isabel I de Castilla "la Catolica" - founder of unified Spain and the
   Reconquista crown personality.

   Historical doctrine:
     - Reconquista (concluded 1492): Isabella's army finished a 700-year
       campaign with Granada. Mapped to a hard offensive baseline and a
       fast Colonial commitment with mass infantry.
     - Tercio precursor: Castilian rodelero swordsmen and pike-shot
       formations were the prototype of the later Tercio. Mapped to a
       deep infantry bias from Colonial on, with the Rodelero as a real
       presence and the Lancer as the wing.
     - Camino del Rey shipment cycle (Spanish civ unique): faster shipments
       fund a steady army stream. Mapped to a moderate Trade Route lean
       and a Forward Operational Line build style.
     - Conquistador legacy: heavy lance cavalry as the shock arm in the
       New World. Mapped to a meaningful cavalry weight that supports the
       infantry rather than leading.
     - Crusade ideology: no native treaty leaning - regulars and Catholic
       military orders only.
*/
//==============================================================================

bool gIsabellaRulesEnabled = false;

void initLeaderIsabella(void)
{
   llVerboseEcho("A New World: activating Isabella I personality.");

   llSetAggressivePersonality();
   btRushBoom = 0.05;             // Light boom; the Reconquista does not wait.
   btOffenseDefense = 0.7;
   btBiasTrade = 0.3;             // Camino del Rey shipment cycle.
   btBiasNative = -0.3;
   llSetMilitaryFocus(0.7, 0.45, 0.3);

   // LL-BUILD-STYLE-BEGIN
   llUseForwardOperationalLineStyle(2);
   gLLMilitaryDistanceMultiplier = 0.90;
   llSetBuildStrongpointProfile(2, 2, 3, true);
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);

   cvOkToBuildForts = true;
   cvMaxTowers = 4;
   cvMaxArmyPop = 120;

   gIsabellaRulesEnabled = true;
   llLogLeaderState("Isabella initialized");
   llProbe("meta.leader_init", "leader=isabella");
}

//------------------------------------------------------------------------------
// Discovery: Castilian assembly. Settler push and Crossbowman trickle;
// the Reconquista forms quickly.
//------------------------------------------------------------------------------
rule isabellaCastilianAssembly
inactive
minInterval 60
{
   llLogRuleTick("isabellaCastilianAssembly");
   if (gIsabellaRulesEnabled == false)
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
// Colonial: Crusading Tempo. Rodelero shock and Crossbowman screen,
// Lancer commitment when the army crystallizes. Forward base posture.
//------------------------------------------------------------------------------
rule isabellaCrusadingTempo
inactive
minInterval 50
{
   llLogRuleTick("isabellaCrusadingTempo");
   if (gIsabellaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = 0.0;
      btOffenseDefense = 0.75;
      btBiasInf = 0.85;
      btBiasCav = 0.55;            // Lancer wing.
      btBiasArt = -0.2;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Fortress: Tercio precursor. Pikeman + Musketeer block, Rodelero shock,
// Lancer wing, Falconet support. The Castilian field army.
//------------------------------------------------------------------------------
rule isabellaTercioPrecursor
inactive
minInterval 55
{
   llLogRuleTick("isabellaTercioPrecursor");
   if (gIsabellaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 0.95;
      btBiasCav = 0.6;
      btBiasArt = 0.4;
      cvMaxArmyPop = 135;
   }
}

//------------------------------------------------------------------------------
// Industrial: Hapsburg succession campaign. Heavy Cannon and Falconet
// park, Musketeer / Pikeman mass continues, Lancer reserve.
//------------------------------------------------------------------------------
rule isabellaHapsburgCampaign
inactive
minInterval 70
{
   llLogRuleTick("isabellaHapsburgCampaign");
   if (gIsabellaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.9;
      btBiasInf = 1.0;
      btBiasCav = 0.65;
      btBiasArt = 0.65;
      cvMaxArmyPop = 150;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Catholic Monarch supremacy - maximum Pikeman / Musketeer /
// Heavy Cannon mass with continuous Lancer pressure on the wings.
//------------------------------------------------------------------------------
rule isabellaCatholicSupremacy
inactive
minInterval 90
{
   llLogRuleTick("isabellaCatholicSupremacy");
   if (gIsabellaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 1.0;
      btBiasCav = 0.7;
      btBiasArt = 0.8;
      cvMaxArmyPop = 165;
   }
}

void enableLeaderIsabellaRules(void)
{
   if (gIsabellaRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("isabellaCastilianAssembly");
   xsEnableRule("isabellaCrusadingTempo");
   xsEnableRule("isabellaTercioPrecursor");
   xsEnableRule("isabellaHapsburgCampaign");
   xsEnableRule("isabellaCatholicSupremacy");
}
