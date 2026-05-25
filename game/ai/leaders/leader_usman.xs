//==============================================================================
/* leader_usman.xs

   Muhammadu Kanta of Kebbi - Hausa heartland personality.

   File-name kept as 'usman' because the engine personality ID (set via
   gLLLeaderKey in leaderCommon.xs::llAssignLeaderIdentity()) is "usman" and
   the AI loader indexes rule-set names from this token. All user-visible
   strings, comments, and lore have been rebranded to Muhammadu Kanta of
   the Kebbi Kingdom — the actual native Hausa figure (16th-century, the
   only kingdom to resist Songhai expansion at the Battle of Tabkin Kwatto)
   rather than the Fulani Sokoto founder Usman dan Fodio, who was a
   conqueror OF the Hausa rather than one of them. Same XS function and
   rule names preserve the engine's dispatch graph; only the doctrine
   narrative has shifted.

   Historical doctrine (Kanta of Kebbi):
     - Tabkin Kwatto (1517): Kanta's federated Hausa cavalry routed the
       Songhai imperial army by combining native horse with traditional
       Hausa archery — mapped here to a balanced infantry/cavalry weight.
     - Surame fortified capital: Kebbi's stone-walled stronghold housing
       the royal household and granaries — mapped to the Distributed
       Economic Network style around a defensible interior anchor.
     - Trans-Saharan trade lattice: Kebbi sat athwart the Niger-bend
       caravan routes — gold, salt, kola — funding the army through
       commerce rather than tribute. btBiasTrade = 0.3 reflects this.
     - Influence economy (Hausa civ unique): Palaces and Influence-gated
       upgrades reward a sprawling, building-led layout. Distributed
       Economic Network handles the spatial expression.
     - Desert mobility: Desert Archer screens, Raider sweeps, Mortar Crews
       cracking fortified positions in the Industrial age.
*/
//==============================================================================

bool gUsmanRulesEnabled = false;

void initLeaderUsman(void)
{
   llVerboseEcho("A New World: activating Muhammadu Kanta of Kebbi personality.");

   llSetAggressivePersonality();
   btRushBoom = 0.1;              // Light boom; the jihad starts early.
   btOffenseDefense = 0.6;
   btBiasTrade = 0.3;             // Trans-Saharan trade funds the Caliphate.
   btBiasNative = 0.2;
   llSetMilitaryFocus(0.45, 0.55, 0.2);  // Cavalry-leaning composition.

   // LL-BUILD-STYLE-BEGIN
   llUseDistributedEconomicNetworkStyle(2);
   gLLEconomicDistanceMultiplier = 1.30;
   // Spec override: military_distance_band [1.1, 1.3]; DistributedEcoNetwork
   // default is 1.0 which falls below the band floor.
   gLLMilitaryDistanceMultiplier = 1.10;
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.72, 0.28, 2, 3.5);

   cvOkToBuildForts = true;
   cvMaxTowers = 4;
   cvMaxArmyPop = 115;

   gUsmanRulesEnabled = true;
   llLogLeaderState("Kanta initialized");
   llProbe("meta.leader_init", "leader=usman");
}

//------------------------------------------------------------------------------
// Discovery: Caravan boom. Trade Route and Settler push first; Influence
// economy needs the buildings before the raids.
//------------------------------------------------------------------------------
rule usmanCaravanBoom
inactive
minInterval 60
{
   llLogRuleTick("usmanCaravanBoom");
   if (gUsmanRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.15;
      btBiasTrade = 0.45;
      cvMinNumVills = 16;
   }
}

//------------------------------------------------------------------------------
// Colonial: Fula raid. Raider and Desert Archer pressure on enemy trade
// lines, Fula Warrior commitment when the army crystallizes.
//------------------------------------------------------------------------------
rule usmanFulaRaid
inactive
minInterval 50
{
   llLogRuleTick("usmanFulaRaid");
   if (gUsmanRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasInf = 0.55;
      btBiasCav = 0.7;             // Raider as the early hammer.
      btBiasArt = -0.4;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Fortress: Caliphate expansion. Lifidi Knight shock cavalry assembles,
// Maigadi guards the line, Desert Archer screens. The state takes the field.
//------------------------------------------------------------------------------
rule usmanCaliphateExpansion
inactive
minInterval 55
{
   llLogRuleTick("usmanCaliphateExpansion");
   if (gUsmanRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.8;
      btBiasInf = 0.7;
      btBiasCav = 0.85;            // Lifidi Knight is the centerpiece.
      btBiasArt = 0.2;
      btBiasTrade = 0.35;
      cvMaxArmyPop = 130;
   }
}

//------------------------------------------------------------------------------
// Industrial: Sokoto state war. Cannon Crews and Mortar Crews crack
// fortified positions; Lifidi Knight mass continues.
//------------------------------------------------------------------------------
rule usmanSokotoWar
inactive
minInterval 70
{
   llLogRuleTick("usmanSokotoWar");
   if (gUsmanRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 0.85;
      btBiasCav = 0.9;
      btBiasArt = 0.55;
      cvMaxArmyPop = 145;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Caliphate host. Maximum Lifidi / Fula / Raider mass with
// Mortar Crews shaping the field; Trans-Saharan trade still funding.
//------------------------------------------------------------------------------
rule usmanCaliphateHost
inactive
minInterval 90
{
   llLogRuleTick("usmanCaliphateHost");
   if (gUsmanRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 0.9;
      btBiasCav = 1.0;
      btBiasArt = 0.7;
      btBiasTrade = 0.45;
      cvMaxArmyPop = 160;
   }
}

void enableLeaderUsmanRules(void)
{
   if (gUsmanRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("usmanCaravanBoom");
   xsEnableRule("usmanFulaRaid");
   xsEnableRule("usmanCaliphateExpansion");
   xsEnableRule("usmanSokotoWar");
   xsEnableRule("usmanCaliphateHost");
}
