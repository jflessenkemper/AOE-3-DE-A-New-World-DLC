//==============================================================================
// aiStateSnapshot.xs — Phase-4 state-trajectory probe.
//
// Emits a `state.snapshot` line every 30s of game time so the offline
// validator (tools/validation/state_snapshot_validator.py) can compare
// the per-civ state trajectory against a recorded baseline and flag
// silent divergence (population drift, age-up timing, resource skew,
// army composition wander).
//
// All emission goes through anwProbe(), which:
//   • Triple-emits via aiEcho + aiChat-to-host + aiChat-to-self so the
//     marker lands in match.log regardless of which sink the runner
//     scrapes.
//   • Honours the global cANWReplayProbes kill switch in aiGlobals.xs —
//     a release build flips that bool and the rule self-disables on the
//     next tick (see the early-out below).
//
// Tag emitted (every 30s):
//   state.snapshot  ageMs=<int> age=<int>
//                   pop_used=<int> pop_cap=<int>
//                   food=<int> wood=<int> gold=<int>
//                   infantry=<int> cavalry=<int> artillery=<int>
//                   warship=<int> villager=<int>
//                   landmil=<int>
//
// Kept tiny on purpose — query budget is identical to the existing
// anwDoctrineProbes rule (a handful of cached kbUnitCount calls + three
// kbResourceGet calls), so per-tick cost is well under a millisecond.
//==============================================================================

// Snapshot interval — 30s game time, matches the rule's own minInterval
// so we emit on every fire (no double-gating like the doctrine probe's
// 60s sub-interval). The validator down-samples if it wants coarser
// resolution.
extern const int cANWStateSnapshotIntervalMs = 30000;

// Last emission, in game ms. -1 = never emitted yet.
extern int gANWLastStateSnapshotMs = -1;


//------------------------------------------------------------------------------
// anwEmitStateSnapshot — collect the cheap-to-query state and ship it
// off as a single anwProbe line. Called from the rule body below.
//------------------------------------------------------------------------------
void anwEmitStateSnapshot(int ageMs = 0)
{
   // Population --------------------------------------------------------------
   int popUsed = kbGetPop();
   int popCap  = kbGetPopCap();

   // Resources ---------------------------------------------------------------
   // kbResourceGet returns float; truncating to int is fine — the
   // validator tolerates ±5% variance and never compares fractional
   // resource counts.
   int food = 0 + kbResourceGet(cResourceFood);
   int wood = 0 + kbResourceGet(cResourceWood);
   int gold = 0 + kbResourceGet(cResourceGold);

   // Unit composition --------------------------------------------------------
   int vil  = kbUnitCount(cMyID, cUnitTypeAbstractVillager,         cUnitStateAlive);
   int inf  = kbUnitCount(cMyID, cUnitTypeAbstractInfantry,         cUnitStateAlive);
   int cav  = kbUnitCount(cMyID, cUnitTypeAbstractCavalry,          cUnitStateAlive);
   int arty = kbUnitCount(cMyID, cUnitTypeAbstractArtillery,        cUnitStateAlive);
   int land = kbUnitCount(cMyID, cUnitTypeLogicalTypeLandMilitary,  cUnitStateAlive);

   // Warship count (only meaningful if civ has a warship abstract type;
   // gANWAbstractWarShip mirrors the pattern in aiNavalUtilities.xs).
   int navy = 0;
   if (gANWAbstractWarShip > 0)
   {
      navy = kbUnitCount(cMyID, gANWAbstractWarShip, cUnitStateAlive);
   }

   anwProbe("state.snapshot",
      "ageMs=" + ageMs +
      " age=" + kbGetAge() +
      " pop_used=" + popUsed +
      " pop_cap="  + popCap +
      " food=" + food +
      " wood=" + wood +
      " gold=" + gold +
      " villager="  + vil +
      " infantry="  + inf +
      " cavalry="   + cav +
      " artillery=" + arty +
      " warship="   + navy +
      " landmil="   + land);
}


//==============================================================================
// anwStateSnapshot — periodic state-trajectory rule. Enabled from
// aiLoaderStandard.xs alongside anwDoctrineProbes when probes are on.
//
// minInterval=30 (game seconds) — matches the snapshot cadence so we
// emit on every fire. The interval-guard below is a belt-and-braces
// check against rule re-entry (XS schedules can fire slightly early
// when the engine is catching up after a slow tick).
//==============================================================================
rule anwStateSnapshot
inactive
minInterval 30
{
   // Bail cheaply when the global probe channel is off — release builds
   // ship with cANWReplayProbes=false, so the rule body becomes a single
   // boolean check per tick and then permanently self-disables.
   if (cANWReplayProbes == false)
   {
      xsDisableSelf();
      return;
   }

   int nowMs = xsGetTime();

   // Interval guard — only emit if we're past the configured interval
   // since the last snapshot (or this is the first emission).
   if (gANWLastStateSnapshotMs >= 0 &&
      (nowMs - gANWLastStateSnapshotMs) < cANWStateSnapshotIntervalMs)
   {
      return;
   }

   anwEmitStateSnapshot(nowMs);
   gANWLastStateSnapshotMs = nowMs;
}
