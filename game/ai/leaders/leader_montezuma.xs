//==============================================================================
/* leader_montezuma.xs

   Motecuhzoma Xocoyotzin (Montezuma II) - Aztec Triple Alliance personality.

   Historical doctrine:
     - Xochiyaoyotl ("Flower War"): ritualized infantry warfare emphasizing
       close-quarters dueling rather than wholesale slaughter.
     - No cavalry, no artillery in real life - pure foot warbands of
       Macehualtin commoners, Eagle/Jaguar/Skull Knights, and ranged
       Atlatl skirmishers (modelled in-game by the Arrow Knight).
     - Tribute economy: conquered altepetl (city-states) paid food, cotton,
       feathers and obsidian. Translates here to map-control aggression
       and a heavy native-alliance bias.
     - Tenochtitlan sat behind causeways and chinampas (raised garden
       beds), so the build style is a Compact Fortified Core with no
       artillery investment whatsoever.
*/
//==============================================================================

bool gMontezumaRulesEnabled = false;

void initLeaderMontezuma(void)
{
   llVerboseEcho("A New World: activating Motecuhzoma II personality.");

   llSetAggressivePersonality();
   btRushBoom = 0.55;          // Boom first, Flower War second.
   btOffenseDefense = 0.6;
   btBiasTrade = -0.5;         // Tribute, not commerce - smash trade routes.
   btBiasNative = 0.7;         // Tlaxcalan, Zapotec, Otomi auxiliaries.
   llSetMilitaryFocus(0.85, 0.05, -0.9);  // All-infantry doctrine, no artillery investment.

   // LL-BUILD-STYLE-BEGIN
   llUseJungleGuerrillaNetworkStyle(0);   // War Huts + chokes; no perimeter wall.
   // Spec override: Aztecs Montezuma doctrine — wall the chokes (Tlaxcala
   // border + causeway entries). The Jungle Guerrilla helper assigns
   // MobileNoWalls(5) by default; spec/playstyle_spec.json wants
   // ChokepointSegments(1) to lock down causeway approaches.
   gLLWallStrategy = cLLWallStrategyChokepointSegments;
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.7, 0.3, 1, 3.0);

   cvMaxTowers = 3;            // The causeways are the wall.
   cvOkToBuildForts = false;   // Aztecs cannot build forts; safety guard.
   cvMaxArmyPop = 110;         // Will scale with age in rules below.

   gMontezumaRulesEnabled = true;
   llLogLeaderState("Montezuma initialized");
   llProbe("meta.leader_init", "leader=montezuma");
}

//------------------------------------------------------------------------------
// Discovery: tribute boom. Push villagers, claim every Trade Post on natives,
// scout aggressively with the War Chief.
//------------------------------------------------------------------------------
rule montezumaTributeBoom
inactive
minInterval 60
{
   llLogRuleTick("montezumaTributeBoom");
   if (gMontezumaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = 0.75;       // Heavier eco lean before Colonial.
      btBiasNative = 0.8;
      cvMinNumVills = 18;      // Push villager count up early.
   }
}

//------------------------------------------------------------------------------
// Colonial: open the Flower War. First wave of Macehualtin and Puma Spearmen
// pressures forward villagers and trade routes. War Chief leads raids.
//------------------------------------------------------------------------------
rule montezumaFlowerWars
inactive
minInterval 50
{
   llLogRuleTick("montezumaFlowerWars");
   if (gMontezumaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = 0.4;        // Pivot from boom to pressure.
      btOffenseDefense = 0.75;
      btBiasInf = 0.95;        // Macehualtin / Puma Spearmen flood.
      btBiasCav = 0.15;        // A trickle of Coyote Runners for chasing.
      btBiasArt = -0.9;        // Refuse Arrow Knights this age - save xp.
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Fortress: Eagle Runner Knights become the anti-cav backbone. Skull Knights
// arrive from the deck. Tezcatlipoca temple if available. Tribute escalates.
//------------------------------------------------------------------------------
rule montezumaEagleAscension
inactive
minInterval 55
{
   llLogRuleTick("montezumaEagleAscension");
   if (gMontezumaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 1.0;         // Eagle Runners + Skull Knights mass.
      btBiasCav = 0.1;
      btBiasArt = -0.6;        // Light Arrow Knight presence allowed.
      btBiasTrade = -0.7;      // Crush enemy trade as tribute extraction.
      cvMaxArmyPop = 130;
   }
}

//------------------------------------------------------------------------------
// Industrial: Jaguar Knight death-stack, Arrow Knight ranged backbone, forward
// plaza near the contested line. War Dance constant.
//------------------------------------------------------------------------------
rule montezumaJaguarStack
inactive
minInterval 75
{
   llLogRuleTick("montezumaJaguarStack");
   if (gMontezumaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 1.0;
      btBiasArt = -0.3;        // Now welcome Arrow Knight shipments.
      cvMaxArmyPop = 145;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: pure Aztec stack - Jaguar/Skull/Eagle/Macehualtin/Coyote, no
// foreign mercenaries. Population pushed to ceiling, full tribute aggression.
//------------------------------------------------------------------------------
rule montezumaTripleAlliance
inactive
minInterval 90
{
   llLogRuleTick("montezumaTripleAlliance");
   if (gMontezumaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btRushBoom = 0.2;
      btOffenseDefense = 1.0;
      btBiasInf = 1.0;
      btBiasArt = -0.2;
      btBiasNative = 0.9;      // Full Triple Alliance auxiliaries.
      cvMaxArmyPop = 160;
   }
}

void enableLeaderMontezumaRules(void)
{
   if (gMontezumaRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("montezumaTributeBoom");
   xsEnableRule("montezumaFlowerWars");
   xsEnableRule("montezumaEagleAscension");
   xsEnableRule("montezumaJaguarStack");
   xsEnableRule("montezumaTripleAlliance");
}
