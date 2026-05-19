//==============================================================================
/* leader_valette.xs

   Jean Parisot de Valette - Grand Master, Sovereign Military Order of Malta
   personality. The defender of the Great Siege of 1565.

   Historical doctrine:
     - Great Siege of Malta (1565): a four-month defense by 6,000 Knights
       and Maltese against ~40,000 Ottomans. Mapped to a hard defensive
       baseline, maximum tower count, and a fort-anchored Compact
       Fortified Core build style.
     - Hospitaller heavy infantry: Knights of St. John fought as armored
       infantry, not cavalry, behind the bastions. Mapped to a strong
       infantry bias and a near-zero cavalry weight.
     - Maltese civ Order Galleys + Auxiliary economy: tribute-based, no
       trade routes in the conventional sense. Mapped to a moderate trade
       lean with native treaties refused (regulars and the Order only).
     - Counter-siege artillery: Maltese kept big guns trained on the
       Ottoman beachhead. Mapped to a real artillery share from Fortress.
     - Fixed Gun, Hospitaller, Sentinel, Pikeman line - the Order's
       composition is recognizable through the entire game.
*/
//==============================================================================

bool gValetteRulesEnabled = false;

void initLeaderValette(void)
{
   llVerboseEcho("A New World: activating Jean Parisot de Valette personality.");

   llSetDefensivePersonality();
   btRushBoom = -0.45;            // Hard boom; the bastions come first.
   btOffenseDefense = -0.35;      // Defensive doctrine of the Order.
   btBiasTrade = 0.2;
   btBiasNative = -0.4;           // Order and regulars only.
   llSetMilitaryFocus(0.85, -0.4, 0.45);

   // LL-BUILD-STYLE-BEGIN
   llUseHighlandCitadelStyle(5);
   llSetBuildStrongpointProfile(4, 3, 2, false);
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.9, 0.1, 2, 5.0);

   cvOkToBuildForts = true;
   cvMaxTowers = 10;              // Maximum bastion network.
   cvMaxArmyPop = 110;
   cvDefenseReflexRadiusActive = 80.0;
   cvDefenseReflexSearchRadius = 80.0;
   cvDefenseReflexRadiusPassive = 35.0;

   gValetteRulesEnabled = true;
   llLogLeaderState("Valette initialized");
   llProbe("meta.leader_init", "leader=jean");
}

//------------------------------------------------------------------------------
// Discovery: Bastion plan. Settler push and early walls; the Order
// prepares the ground.
//------------------------------------------------------------------------------
rule valetteBastionPlan
inactive
minInterval 60
{
   llLogRuleTick("valetteBastionPlan");
   if (gValetteRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.7;
      cvMinNumVills = 18;
   }
}

//------------------------------------------------------------------------------
// Colonial: Pikeman bastion. Pikeman / Sentinel mass behind walls and
// towers; Crossbowman screen. Refuses cavalry, refuses field engagement.
//------------------------------------------------------------------------------
rule valettePikemanBastion
inactive
minInterval 50
{
   llLogRuleTick("valettePikemanBastion");
   if (gValetteRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = -0.3;
      btOffenseDefense = -0.2;
      btBiasInf = 0.85;
      btBiasCav = -0.5;
      btBiasArt = -0.2;
      cvMinNumVills = 32;
   }
}

//------------------------------------------------------------------------------
// Fortress: Hospitaller line. Hospitaller heavy infantry, Fixed Gun
// emplacements, Sentinel guards. The Great Siege footprint forms.
//------------------------------------------------------------------------------
rule valetteHospitallerLine
inactive
minInterval 55
{
   llLogRuleTick("valetteHospitallerLine");
   if (gValetteRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.0;
      btBiasInf = 1.0;
      btBiasCav = -0.4;
      btBiasArt = 0.55;            // Counter-siege artillery.
      cvMaxArmyPop = 125;
      cvMaxTowers = 12;
   }
}

//------------------------------------------------------------------------------
// Industrial: Counter-siege park. Heavy Cannon and Mortar park, Hospitaller
// mass, fort line creeps forward. The Order takes the ground it can hold.
//------------------------------------------------------------------------------
rule valetteCounterSiegePark
inactive
minInterval 70
{
   llLogRuleTick("valetteCounterSiegePark");
   if (gValetteRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.25;
      btBiasInf = 1.0;
      btBiasArt = 0.75;
      cvMaxArmyPop = 140;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Order of St. John supremacy - Hospitaller / Sentinel / Heavy
// Cannon / Mortar block, near-zero cavalry, full bastion overlay.
//------------------------------------------------------------------------------
rule valetteOrderSupremacy
inactive
minInterval 90
{
   llLogRuleTick("valetteOrderSupremacy");
   if (gValetteRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.5;
      btBiasInf = 1.0;
      btBiasCav = -0.2;
      btBiasArt = 0.9;
      cvMaxArmyPop = 155;
   }
}

void enableLeaderValetteRules(void)
{
   if (gValetteRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("valetteBastionPlan");
   xsEnableRule("valettePikemanBastion");
   xsEnableRule("valetteHospitallerLine");
   xsEnableRule("valetteCounterSiegePark");
   xsEnableRule("valetteOrderSupremacy");
}
