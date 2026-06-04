//==============================================================================
/* leader_maurice.xs

   Maurice of Nassau, Prince of Orange - Dutch United Provinces personality.

   Historical doctrine:
     - Drill reforms: Maurice rebuilt the Dutch infantry around volley fire,
       counter-march drill, and standardized small companies. Mapped to a
       hard infantry/skirmisher bias and a refusal of cavalry-led play.
     - Pikeman / shot integration: pike blocks anchored, musket and crossbow
       on the wings. The in-game Halberdier (elite Tericos analogue) plus
       Pikeman / Skirmisher / Musketeer mix matches that exactly.
     - Engineer corps and siege works: Maurice industrialized siegecraft and
       built a permanent corps of engineers. Mapped to a heavy fortification
       and tower investment, plus consistent artillery share.
     - Stadtholder economy: VOC banks and trade fleets paid for the army.
       Mapped to a strong Bank-style trade-route bias and a slow defensive
       opener that pays for the late game with capital, not population.
     - Eighty Years' War: long, methodical war of attrition. Maurice never
       won by surprise; he won by being undefeated for two decades.
*/
//==============================================================================

bool gMauriceRulesEnabled = false;

void initLeaderMaurice(void)
{
   anwVerboseEcho("A New World: activating Maurice of Nassau personality.");

   anwSetDefensivePersonality();
   btRushBoom = -0.45;            // Hard boom; banks finance the war.
   btOffenseDefense = -0.05;      // Defensive baseline.
   btBiasTrade = 0.6;             // VOC trade-route emphasis.
   btBiasNative = -0.3;           // Regulars only; no native treaty leaning.
   anwSetMilitaryFocus(0.7, -0.2, 0.35);  // Infantry-heavy, almost no cavalry, real artillery.

   // LL-BUILD-STYLE-BEGIN
   anwUseNavalMercantileCompoundStyle(2);
   gANWEconomicDistanceMultiplier = 1.40;
   gANWHouseDistanceMultiplier = 1.05;
   // LL-BUILD-STYLE-END
   anwSetLeaderTacticalDoctrine(0.85, 0.15, 2, 4.5);   // Stadtholder stays well behind the line.

   cvOkToBuildForts = true;
   cvMaxTowers = 8;               // Engineer corps - lots of towers.
   cvMaxArmyPop = 110;

   gMauriceRulesEnabled = true;
   anwLogLeaderState("Maurice initialized");
   anwProbe("meta.leader_init", "leader=maurice");
}

//------------------------------------------------------------------------------
// Discovery: bank-economy boom. Trade Routes and Settlers first; the army
// comes later.
//------------------------------------------------------------------------------
rule mauriceBankBoom
inactive
minInterval 60
{
   anwLogRuleTick("mauriceBankBoom");
   if (gMauriceRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.7;
      btBiasTrade = 0.75;
      cvMinNumVills = 18;
   }
}

//------------------------------------------------------------------------------
// Colonial: Pikeman / Skirmisher screen with a hard refusal of cavalry.
// Stays behind the perimeter and continues building banks.
//------------------------------------------------------------------------------
rule mauricePikeShotScreen
inactive
minInterval 50
{
   anwLogRuleTick("mauricePikeShotScreen");
   if (gMauriceRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = -0.25;
      btOffenseDefense = 0.1;
      btBiasInf = 0.85;           // Pikeman + Skirmisher combo.
      btBiasCav = -0.4;           // Refuse cavalry, hold the line.
      btBiasArt = -0.3;
      cvMinNumVills = 32;
   }
}

//------------------------------------------------------------------------------
// Fortress: Drill Reforms. Halberdier line, Ruyter pistol-cavalry response,
// Falconet support. The Dutch line is almost impossible to displace.
//------------------------------------------------------------------------------
rule mauriceDrillReforms
inactive
minInterval 55
{
   anwLogRuleTick("mauriceDrillReforms");
   if (gMauriceRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.4;
      btBiasInf = 1.0;            // Halberdier + Musketeer mass.
      btBiasCav = 0.05;           // Only Ruyter as a counter-cavalry tool.
      btBiasArt = 0.45;
      btBiasTrade = 0.7;
      cvMaxArmyPop = 125;
      cvMaxTowers = 9;
   }
}

//------------------------------------------------------------------------------
// Industrial: Engineer Corps. Heavy Cannon and Mortar share rises; the
// Dutch grind forward in a fortified line. Banks underwrite the campaign.
//------------------------------------------------------------------------------
rule mauriceEngineerCorps
inactive
minInterval 70
{
   anwLogRuleTick("mauriceEngineerCorps");
   if (gMauriceRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.6;
      btBiasInf = 1.0;
      btBiasArt = 0.7;            // Mortar + Heavy Cannon emphasis.
      btBiasTrade = 0.7;
      cvMaxArmyPop = 140;
      anwEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Eighty Years' attrition. Halberdier + Skirmisher + Heavy Cannon
// fortress line, near-zero cavalry, maximum bank coverage.
//------------------------------------------------------------------------------
rule mauriceEightyYearsLine
inactive
minInterval 90
{
   anwLogRuleTick("mauriceEightyYearsLine");
   if (gMauriceRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.7;
      btBiasInf = 1.0;
      btBiasCav = 0.0;
      btBiasArt = 0.85;
      btBiasTrade = 0.8;
      cvMaxArmyPop = 155;
   }
}

void enableLeaderMauriceRules(void)
{
   if (gMauriceRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("mauriceBankBoom");
   xsEnableRule("mauricePikeShotScreen");
   xsEnableRule("mauriceDrillReforms");
   xsEnableRule("mauriceEngineerCorps");
   xsEnableRule("mauriceEightyYearsLine");
}
