//==============================================================================
/* anwDifficultyScale.xs — difficulty-aware doctrine execution.

   PRINCIPLE: difficulty scales EXECUTION INTENSITY, never STYLE.
   Each nation keeps its unique historical doctrine (set by its leader file +
   per-civ wall knobs); difficulty only controls how COMPLETELY and
   AGGRESSIVELY that doctrine is executed:

     Expert  = the full historical doctrine, played tight and competitive.
     Sandbox = a beatable, looser version of the SAME doctrine.

   A MobileNoWalls civ (strategy 5) never grows walls on Expert; a turtle never
   abandons them on Sandbox. We scale completeness/aggression, not identity.

   Called from preInit() AFTER anwSetWallKnobsForCiv() so it scales the
   per-civ values. Emits meta.difficulty so the farm/validator knows which
   per-difficulty band to check.
*/
//==============================================================================

extern int gANWDoctrineIntensity = 100;   // 0..100, set per difficulty below

void anwApplyDifficultyScaling(void)
{
   // Intensity by difficulty. Expert/Extreme = full (100).
   int intensity = 100;
   if (cDifficultyCurrent == cDifficultySandbox)       intensity = 25;
   else if (cDifficultyCurrent == cDifficultyEasy)     intensity = 45;
   else if (cDifficultyCurrent == cDifficultyModerate) intensity = 65;
   else if (cDifficultyCurrent == cDifficultyHard)     intensity = 85;
   else                                                intensity = 100;
   gANWDoctrineIntensity = intensity;

   // ---- Wall execution (only for civs that actually wall) -----------------
   if (gANWWallStrategy != cANWWallStrategyMobileNoWalls)
   {
      // Closure target: full doctrine at Expert, leaves gaps on easy.
      // Floor at 35% so even Sandbox attempts a partial ring (not random).
      int clo = (gANWWallClosurePctTarget * intensity) / 100;
      if (clo < 35) clo = 35;
      if (clo > gANWWallClosurePctTarget) clo = gANWWallClosurePctTarget;
      gANWWallClosurePctTarget = clo;

      // Repair urgency scales with difficulty (min 1 = at least lazy repair).
      int rep = (gANWWallRepairAggressiveness * intensity) / 100;
      if (rep < 1) rep = 1;
      gANWWallRepairAggressiveness = rep;

      // Villagers committed to walls: easy commits fewer (range 0.7x..1.0x).
      gANWWallVillagerCount = (gANWWallVillagerCount * (intensity + 40)) / 140;

      // Easier AIs start walling one age later (less proactive).
      if (intensity <= 45 && gANWWallTriggerAge < 5)
         gANWWallTriggerAge = gANWWallTriggerAge + 1;
   }

   // ---- Army commitment (all civs) ----------------------------------------
   // Bigger, more committed army at higher difficulty (0.85x..1.15x band).
   if (cvMaxArmyPop > 0)
      cvMaxArmyPop = (cvMaxArmyPop * (intensity + 70)) / 170;

   // ---- Forward aggression timing (all civs) ------------------------------
   // Higher difficulty pushes the forward base earlier; easy delays it.
   // (lower earliestMs = earlier).  +0s at Expert .. +450s at Sandbox.
   gANWForwardBaseEarliestMs = gANWForwardBaseEarliestMs + ((100 - intensity) * 6000);

   anwProbe("meta.difficulty",
      "diff=" + cDifficultyCurrent +
      " intensity=" + intensity +
      " closure=" + gANWWallClosurePctTarget +
      " repair=" + gANWWallRepairAggressiveness +
      " wallVils=" + gANWWallVillagerCount +
      " trigAge=" + gANWWallTriggerAge +
      " army=" + cvMaxArmyPop +
      " fwdMs=" + gANWForwardBaseEarliestMs);
}
