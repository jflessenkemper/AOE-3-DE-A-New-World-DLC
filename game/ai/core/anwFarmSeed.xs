//==============================================================================
/* anwFarmSeed.xs — AI Simulation-Farm determinism hook.

   Lets the farm driver seed every AI's RNG identically across re-runs so the
   same (civ, map, slate, seed) produces a reproducible match — the basis of
   the Phase-0 determinism check (see docs/SIM_FARM_IMPLEMENTATION_PLAN.md).

   How it works:
     - gANWFarmSeed defaults to 0 == DISABLED, so normal play is a no-op and
       gameplay is completely unaffected when the farm isn't running.
     - The farm driver overwrites the single value line below in the DEPLOYED
       copy of this file
         (.../mods/local/A New World/game/ai/core/anwFarmSeed.xs)
       before each match, then launches. XS recompiles per match, so the new
       seed takes effect on the next game.
     - anwApplyFarmSeed() is called once from preInit() (aiLoaderStandard.xs),
       before any AI decision is made.

   The value line is machine-edited; keep it on its own line in the exact form
   `extern int gANWFarmSeed = <int>;` so the driver's regex can find it.
*/
//==============================================================================

extern int gANWFarmSeed = 0;   // FARM-DRIVER-PATCHED — keep on one line

void anwApplyFarmSeed(void)
{
   if (gANWFarmSeed == 0)
   {
      return;   // disabled — normal play, no determinism override
   }
   aiRandSetSeed(gANWFarmSeed);
   anwProbe("match.seed", "seed=" + gANWFarmSeed);
}
