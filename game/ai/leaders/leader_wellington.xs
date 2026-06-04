//==============================================================================
/* leader_wellington.xs

   Queen Elizabeth I of England (Tudor, r. 1558-1603) - lobby-matched British
   leader. File name kept as "wellington" because the engine personality ID
   is "Wellington" (personalities.xml); the function and rule names preserve
   that key for the engine's AI dispatch. All user-visible strings, knobs,
   and portraits have been rebranded to Elizabeth's doctrine.

   Historical doctrine:
     - Sea Dogs and privateer fleet: Drake, Hawkins, Frobisher - English
       sea power broke the Spanish Armada in 1588 and harried the Spanish
       silver line through Elizabeth's reign. Mapped to a very heavy naval
       and trade bias and a coastal sprawl economy.
     - Trained Bands militia: Tudor England had no standing army; defense
       was the county levy of yeoman longbowmen and billmen. Mapped to
       Longbowman emphasis and modest professional force size, rather than
       Wellington's continental Redcoat mass.
     - Merchant Adventurers and Royal Exchange (1566): Elizabethan England
       ran on chartered trading companies (Muscovy 1555, Levant 1581, East
       India 1600). Mapped to strong Trade Route lean and mercantile
       compound build style.
     - Armada defense posture: insular and cautious, committing the fleet
       to decisive naval action but avoiding continental land adventure.
       Mapped to a defensive baseline that only leans offensive late.
     - Tudor artillery was modest (shipboard more than field); Elizabeth
       did not fight Napoleonic-style gun lines. Mapped to reduced artillery
       share compared with the prior Wellington tuning.
*/
//==============================================================================

bool gWellingtonRulesEnabled = false;

void initLeaderWellington(void)
{
   anwVerboseEcho("A New World DLC: activating Queen Elizabeth I personality.");

   anwSetDefensivePersonality();
   btRushBoom = -0.4;             // Tudor boom; island kingdom grows behind the fleet.
   btOffenseDefense = 0.2;        // Defensive baseline; Elizabeth avoided continental war.
   btBiasTrade = 0.7;             // Muscovy / Levant / East India Co. mercantile chartering.
   btBiasNative = -0.1;           // Regulars and trained bands; sparing use of auxiliaries.
   anwSetMilitaryFocus(0.75, 0.10, 0.15); // Longbow + Musketeer primacy; minimal field artillery.

   // LL-BUILD-STYLE-BEGIN
   anwUseNavalMercantileCompoundStyle(2);
   gANWEconomicDistanceMultiplier = 1.40;         // Coastal-sprawl eco network.
   gANWTownCenterDistanceMultiplier = 1.25;       // Spread TCs along shoreline.
   gANWEarlyWallingEnabled = false;               // Island identity - navy guards early,
                                                 // no inland continental wall rings.
                                                 // Late walls still fire via CoastalBatteries.
   // LL-BUILD-STYLE-END
   anwSetLeaderTacticalDoctrine(0.82, 0.18, 2, 4.0);   // Leader well behind the firing line.

   cvOkToBuildForts = true;
   cvOkToFish = true;                            // Explicit maritime identity - North Sea fishing fleet.
   cvMaxTowers = 8;                              // Martello chain base (scales up by age).
   cvMaxArmyPop = 110;
   cvMaxCivPop = 120;                            // Manor economy supports large vill pop.

   // Reverse-slope defense: hold the line firmly, don't chase.
   cvDefenseReflexRadiusActive = 70.0;           // Strong defensive perimeter.
   cvDefenseReflexRadiusPassive = 25.0;          // Don't overextend when regrouping.
   cvDefenseReflexSearchRadius = 70.0;           // Detect at perimeter edge.

   gWellingtonRulesEnabled = true;
   anwLogLeaderState("Elizabeth I initialized");
   anwProbe("meta.leader_init", "leader=wellington");
}

//------------------------------------------------------------------------------
// Discovery: Manor boom and explorer scouting. Wellington spent weeks
// surveying ground before any campaign - reflected as heavy scouting and
// villager push.
//------------------------------------------------------------------------------
rule wellingtonManorBoom
inactive
minInterval 60
{
   anwLogRuleTick("wellingtonManorBoom");
   if (gWellingtonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.6;          // Hard boom into Colonial.
      btBiasTrade = 0.45;         // Trade Route emphasis - Royal Navy doctrine.
      cvMinNumVills = 18;
   }
}

//------------------------------------------------------------------------------
// Colonial: Longbowmen as area-denial skirmishers, fast Manor sprawl, light
// Hussar screen. Wellington avoided early adventure - hold ground and grow.
//------------------------------------------------------------------------------
rule wellingtonLongbowScreen
inactive
minInterval 50
{
   anwLogRuleTick("wellingtonLongbowScreen");
   if (gWellingtonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = -0.1;
      btOffenseDefense = 0.35;
      btBiasInf = 0.85;           // Longbow + transitional musket presence.
      btBiasCav = 0.1;            // Light Hussar screen.
      btBiasArt = -0.4;           // No real artillery yet; save xp.
      cvMinNumVills = 30;
   }
}

//------------------------------------------------------------------------------
// Fortress: the Redcoat (Musketeer) age. Drilled line infantry mass with
// Falconet flank support and KGL Hussar / Dragoon counter-charge. Forward
// base anchored well within own defensive perimeter (the Lines of Torres
// Vedras analogue).
//------------------------------------------------------------------------------
rule wellingtonRedcoatLine
inactive
minInterval 55
{
   anwLogRuleTick("wellingtonRedcoatLine");
   if (gWellingtonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.55;
      btBiasInf = 1.0;            // Redcoat mass.
      btBiasCav = 0.35;           // KGL Hussar / Dragoon counter-strike.
      btBiasArt = 0.5;            // Falconet support arrives.
      cvMaxArmyPop = 125;
      anwEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Industrial: Iberian-Peninsula style. Ranger mercenaries from the Saloon,
// Heavy Cannon punch, dense Manor sprawl. The army stops being defensive
// and starts grinding the front line forward in disciplined steps.
//------------------------------------------------------------------------------
rule wellingtonIberianGrind
inactive
minInterval 70
{
   anwLogRuleTick("wellingtonIberianGrind");
   if (gWellingtonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.7;
      btBiasInf = 1.0;
      btBiasCav = 0.3;
      btBiasArt = 0.7;            // Heavy Cannon and Howitzer share rises.
      cvMaxArmyPop = 140;
      cvMaxTowers = 8;
   }
}

//------------------------------------------------------------------------------
// Imperial: Iron Duke fortified-line warfare. Maximum Redcoat plus Heavy
// Cannon weight, KGL cavalry reserves, fort-anchored advance. Wellington
// at Waterloo: stand the line, let them break, then walk forward.
//------------------------------------------------------------------------------
rule wellingtonIronDuke
inactive
minInterval 90
{
   anwLogRuleTick("wellingtonIronDuke");
   if (gWellingtonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btRushBoom = -0.1;          // Still growing; Tudor reign preferred eco strength.
      btOffenseDefense = 0.65;    // Measured offensive - Armada-year resolve, not blitz.
      btBiasInf = 1.0;
      btBiasCav = 0.3;
      btBiasArt = 0.4;            // Modest artillery - Tudor doctrine, not Napoleonic gun line.
      cvMaxArmyPop = 150;
      anwEnableForwardBaseStyle();
   }
}

void enableLeaderWellingtonRules(void)
{
   if (gWellingtonRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("wellingtonManorBoom");
   xsEnableRule("wellingtonLongbowScreen");
   xsEnableRule("wellingtonRedcoatLine");
   xsEnableRule("wellingtonIberianGrind");
   xsEnableRule("wellingtonIronDuke");
}
