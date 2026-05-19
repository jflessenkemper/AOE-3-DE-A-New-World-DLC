//==============================================================================
/* leader_washington.xs

   General George Washington - Continental Army commander and first
   President of the United States personality.

   Historical doctrine:
     - Continental Army: long-service Continentals trained on European
       lines (von Steuben drill at Valley Forge), supplemented by state
       militia. Mapped to a deep infantry bias and a real but supporting
       cavalry weight.
     - Fabian strategy (1776-1777): Washington avoided pitched battle when
       outclassed, preserved the army, struck at Trenton/Princeton when
       conditions favored. Mapped to a defensive-leaning Discovery and
       Colonial that converts to a hard offensive at Fortress.
     - State militia (US civ unique): State Capitols, State Militia, and
       a sprawling civic economy. Mapped to the Civic Militia Center
       build style.
     - Continental artillery (Knox's gun park, Yorktown 1781): real
       artillery share at Industrial. Heavy Cannon and Mortar by Imperial.
     - Native frontier policy: mixed - some treaties (Iroquois,
       Stockbridge), some campaigns. Mapped to a slight Native Treaty
       lean rather than a strong one.
*/
//==============================================================================

bool gWashingtonRulesEnabled = false;

void initLeaderWashington(void)
{
   llVerboseEcho("A New World: activating George Washington personality.");

   llSetBalancedPersonality();
   btRushBoom = -0.15;            // Hard boom; Continental Army needs the supply train.
   btOffenseDefense = 0.25;       // Defensive baseline that ramps later.
   btBiasTrade = 0.1;
   btBiasNative = 0.1;
   llSetMilitaryFocus(0.7, 0.3, 0.4);

   // LL-BUILD-STYLE-BEGIN
   llUseRepublicanLeveeStyle(1);
   gLLTownCenterDistanceMultiplier = 1.10;
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.78, 0.22, 2, 4.0);

   cvOkToBuildForts = true;
   cvMaxTowers = 5;
   cvMaxArmyPop = 115;

   gWashingtonRulesEnabled = true;
   llLogLeaderState("Washington initialized");
   llProbe("meta.leader_init", "leader=washington");
}

//------------------------------------------------------------------------------
// Discovery: Continental Congress. Settler push and State Capitol
// placement; the Republic organizes before it fights.
//------------------------------------------------------------------------------
rule washingtonContinentalCongress
inactive
minInterval 60
{
   llLogRuleTick("washingtonContinentalCongress");
   if (gWashingtonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.4;
      cvMinNumVills = 18;
   }
}

//------------------------------------------------------------------------------
// Colonial: State Militia muster. State Militia and Continental Musketeer
// trickle behind a defensive perimeter; light raids only.
//------------------------------------------------------------------------------
rule washingtonStateMilitiaMuster
inactive
minInterval 50
{
   llLogRuleTick("washingtonStateMilitiaMuster");
   if (gWashingtonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = -0.1;
      btOffenseDefense = 0.35;
      btBiasInf = 0.85;
      btBiasCav = 0.2;
      btBiasArt = -0.1;
      cvMinNumVills = 32;
   }
}

//------------------------------------------------------------------------------
// Fortress: Continental Army. Continental Musketeer mass, State Militia
// reserve, Carbine Cavalry wing, Falconet support. The von Steuben army
// takes the field.
//------------------------------------------------------------------------------
rule washingtonContinentalArmy
inactive
minInterval 55
{
   llLogRuleTick("washingtonContinentalArmy");
   if (gWashingtonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.65;
      btBiasInf = 0.95;
      btBiasCav = 0.5;
      btBiasArt = 0.45;
      cvMaxArmyPop = 130;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Industrial: Yorktown campaign. Knox-style Heavy Cannon park, Continental
// Musketeer mass, Sharpshooter screen. The Republic forces decision.
//------------------------------------------------------------------------------
rule washingtonYorktownCampaign
inactive
minInterval 70
{
   llLogRuleTick("washingtonYorktownCampaign");
   if (gWashingtonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.8;
      btBiasInf = 1.0;
      btBiasCav = 0.55;
      btBiasArt = 0.7;
      cvMaxArmyPop = 145;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Republic at arms - maximum Continental Musketeer / Sharpshooter
// / Heavy Cannon mass with Carbine Cavalry wings; State Militia replenish.
//------------------------------------------------------------------------------
rule washingtonRepublicAtArms
inactive
minInterval 90
{
   llLogRuleTick("washingtonRepublicAtArms");
   if (gWashingtonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.9;
      btBiasInf = 1.0;
      btBiasCav = 0.6;
      btBiasArt = 0.85;
      cvMaxArmyPop = 160;
   }
}

void enableLeaderWashingtonRules(void)
{
   if (gWashingtonRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("washingtonContinentalCongress");
   xsEnableRule("washingtonStateMilitiaMuster");
   xsEnableRule("washingtonContinentalArmy");
   xsEnableRule("washingtonYorktownCampaign");
   xsEnableRule("washingtonRepublicAtArms");
}
