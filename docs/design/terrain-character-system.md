# Design Note: Per-Nation Terrain Character System

**Status:** Draft for review
**Scope:** Broad — all 23 civs, every building type, scout-first TC siting, archetype-driven spending
**Owner:** A New World AI mod
**Date:** 2026-04-24

---

## 1. Problem statement

Today the AI places buildings on a distance-from-main-base basis with light front-vector bias and a handful of unique-building rules (Dutch banks, Japanese shrines, etc.). The result is:

- **Clumped, homogeneous towns** regardless of civ
- **Starting TC inherited blindly** from the map script — no evaluation of whether the terrain fits the nation
- **Expansion TCs dropped at geometric distances**, not at river bends, shorelines, forest edges, mountain passes, or caravan chokepoints
- **No coherent identity** between walls, economy, military, and placement — each system branches on civ independently, so a Dutch town and a Lakota camp can look almost identical from above

We want every nation to feel distinctly itself on the map. The Dutch build along coasts and river deltas with polder-style water-chokepoint walls. The Lakota never build walls, camp near rivers for winter shelter, keep pop mobile. The Hausa ring massive earthen walls around a plains-trade chokepoint. This should be **visible from the minimap** and consistent across every building the AI places.

## 2. Goals

1. **Terrain identity per civ, as data.** One source of truth table indexed by `cMyCiv`, consumed by placement, walling, military siting, and economy.
2. **Scout-first TC siting for expansion TCs and forward bases.** Before committing a TC build plan, the scout must evaluate candidate locations against civ terrain preferences. No more "closest flat spot N tiles forward."
3. **Starting TC is a given — we adapt.** On game start, we assess the terrain the map dealt us and pick an appropriate build-style variant. We don't move the starting TC, but the whole town grows outward along terrain the civ prefers.
4. **Every building is terrain-aware.** Not just TC and mills. Barracks, stables, markets, forts, mosques, shrines, wonders — each has a per-civ terrain affinity.
5. **Spend archetype plugs the resource leak.** The six-way classification (Stockpiler, Reinvestor, Warmaker, Mercantilist, Monumentalist, Subsistence) drives `handleExcessResources` at Age 3+ where it currently falls into `UNHANDLED`.
6. **No regressions.** Works inside existing plan system. Works for Revolution civs via commander lookup. Degrades gracefully if terrain can't be resolved (falls back to today's behavior).

## 3. Engine primitives we have

Confirmed via codebase grep (current usage counts in parens):

| Primitive | Purpose | Usage today |
|---|---|---|
| `kbAreaGroupGetIDByPosition(vec)` | Which land/water group a position is in | 187 calls across 15 files |
| `kbAreAreaGroupsPassableByLand(a, b)` | Are two groups reachable by land | Used in setup + walls |
| `kbUnitCount` / `kbUnitQuerySet*` with filters | Count trees / herdables / enemies near a point | 368 calls across 14 files |
| `cUnitTypeTree` | Forest proximity via tree count in radius | Already used for wood gather scoring |
| `cUnitTypeHerdable` | Herdable presence (food) | Already used for slaughter plans |
| `kbBaseGetFrontVector(cMyID, baseID)` | Known-enemy direction | Used for wall bias |
| `kbBaseGetLocation`, `kbUnitGetPosition` | Basic positioning | Ubiquitous |
| `kbResourceGetAreaID` | Resource node lookups | Mining/hunt plans |
| `aiPlanSetVariableVector(planID, key, idx, vec)` | Steer a plan's target location | Standard idiom |

**What we do NOT have out of the box:**

- Direct "is this tile coast" query (we infer via `kbAreaGroupGetIDByPosition` on a water group vs. land)
- Direct "elevation / mountain" query (AoE3 has cliffs; queryable via `cUnitTypeCliff` is worth testing)
- Direct "chokepoint" detection (we'll derive geometrically — narrow land between two water groups)

**Gap-fill strategy:** build our own terrain-tagging pass at match start (`llTerrainCensus()`) that samples ~400 probe points across the map and tags each with a bitmask: `{HasTreesNear, HasWaterNear, HasMountainNear, IsChokepoint, IsPlainsOpen, IsRiverine}`. Store as a flat `int[]` indexed by grid cell. All later queries are O(1) lookups.

## 4. Character axis table (source of truth)

One row per civ. Columns are what every downstream system reads.

| Civ | Wall Archetype | Terrain Pref 1 | Terrain Pref 2 | Spend Archetype | Military Identity | Labor Bias |
|---|---|---|---|---|---|---|
| British | CoastalBatteries | Coast | Plains | Mercantilist | Naval-backed line infantry | Farm + herd + trade |
| French | FortressRing | Rivers | Plains | Monumentalist | Combined-arms mass + arty | Cereal + viticulture |
| Spanish | CoastalBatteries | Coast | Mountains | Warmaker | Tercio/line + colonial cav | Mesta + Mediterranean |
| Portuguese | CoastalBatteries | Coast | Rivers | Mercantilist | Small pro + naval arty | Fish-heavy + naval timber |
| Dutch | ChokepointSegments | Coast | Rivers | Mercantilist | Compact pro + naval | Dairy + fish + banking |
| Germans | FortressRing | Rivers | Forests | Reinvestor | Landsknecht→Prussian + arty | Forest timber + mining |
| Russians | FrontierPalisades | Plains | Rivers | Warmaker | Mass conscript + Cossack | Serf grain + fur |
| Ottomans | FortressRing | Rivers | Coast | Warmaker | Janissary + sipahi + siege | Wheat + crossroads duties |
| Swedes | CoastalBatteries | Coast | Forests | Warmaker | Aggressive Carolean shock | Iron + forest |
| Italians | FortressRing | Coast | Rivers | Mercantilist | Condottieri mixed arms | Mediterranean + banking |
| Maltese | FortressRing | Coast | Chokepoints | Warmaker | Knight-order siege-defense | Grain import + corsairing |
| Chinese | FrontierPalisades | Rivers | Plains | Monumentalist | Mass crossbow/banner cav | Rice/wheat + silver sink |
| Japanese | FortressRing | Mountains | Coast | Reinvestor | Samurai + ashigaru | Rice + fish + managed forest |
| Indians | FortressRing | Rivers | Mountains | Monumentalist | Elephants + heavy cav + rockets | Textile + caste labor |
| Haudenosaunee | FrontierPalisades | Forests | Rivers | Reinvestor | Forest raid-and-withdraw | Three Sisters + hunt |
| Lakota | MobileNoWalls | Plains | Rivers | Subsistence | Horse-archer raid swarm | Bison hunt |
| Aztecs | ChokepointSegments | Rivers | Mountains | Monumentalist | Eagle/Jaguar + massed levies | Chinampa + tribute |
| Incas | ChokepointSegments | Mountains | Rivers | Stockpiler | Mountain sling/club | Terrace + llama + qollqa |
| Ethiopians | ChokepointSegments | Mountains | Rivers | Monumentalist | Highland spear/sword + guard | Teff + ox-plow |
| Hausa | FortressRing | Plains | Chokepoints | Mercantilist | Armored Sahelian heavy cav | Millet + caravan trade |
| Americans | FrontierPalisades | Rivers | Plains | Reinvestor | Militia + rifle regulars | Family-farm + industrial |
| Mexicans | FrontierPalisades | Mountains | Plains | Warmaker | Line inf + lancero | Hacienda + silver |

**Five wall-doctrine corrections vs. current `leaderCommon.xs`:**

| Leader | Current | Correct per history | Rationale |
|---|---|---|---|
| Catherine (Russia) | FortressRing | **FrontierPalisades** | Great Abatis / Belgorod Line defines Russian defense |
| Hiawatha (Haudenosaunee) | MobileNoWalls | **FrontierPalisades** | Longhouse villages were palisaded; not mobile |
| Tokugawa (Japan) | MobileNoWalls | **FortressRing** | Castle-town geometry is ring-based |
| Shivaji (India) | MobileNoWalls | **FortressRing** | Maratha hill forts are the defining feature |
| Garibaldi (Italy) | UrbanBarricade | **FortressRing** (or keep UrbanBarricade as stylistic republican override) | Italy invented trace italienne |
| Wellington (Britain) | FortressRing | **CoastalBatteries** | Royal Navy + Martello doctrine |

These can stay as-is if the leader is a conscious stylistic override (e.g., Napoleon IS mobile even though France is Fortress). But Hiawatha/Tokugawa/Shivaji being MobileNoWalls looks like error, not choice — verify with owner before flipping.

## 5. Data model

New file `game/ai/core/aiCharacterAxes.xs`, loaded early in preInit.

```xs
// Axis constants
const int cAxisWallArchetype  = 0;
const int cAxisTerrainPref1   = 1;
const int cAxisTerrainPref2   = 2;
const int cAxisSpendArchetype = 3;
const int cAxisLaborBias      = 4;

// Terrain type constants (bitmask-friendly for multi-tag tiles)
const int cTerrainCoast       = 1;
const int cTerrainRivers      = 2;
const int cTerrainForests     = 4;
const int cTerrainPlains      = 8;
const int cTerrainMountains   = 16;
const int cTerrainChokepoints = 32;

// Spend archetypes
const int cSpendStockpiler    = 0;
const int cSpendReinvestor    = 1;
const int cSpendWarmaker      = 2;
const int cSpendMercantilist  = 3;
const int cSpendMonumentalist = 4;
const int cSpendSubsistence   = 5;

// Globals populated in llInitCharacterAxes()
int gMyWallArchetype = -1;
int gMyTerrainPref1  = -1;
int gMyTerrainPref2  = -1;
int gMySpendArchetype = -1;
int gMyLaborBias     = -1;

void llInitCharacterAxes(void)
{
   string civ = llNormalizeCivName(kbGetCivName(cMyCiv));

   if (civ == "British")
   {
      gMyWallArchetype  = cWallCoastalBatteries;
      gMyTerrainPref1   = cTerrainCoast;
      gMyTerrainPref2   = cTerrainPlains;
      gMySpendArchetype = cSpendMercantilist;
      // ...labor bias...
   }
   // ...23 civs total...
}
```

Why globals instead of arrays: XS globals are cheap and there's exactly one `cMyCiv` per match. Revolution civs get handled by the `llNormalizeCivName` table, which already exists and was extended in the previous commit.

## 6. Terrain census at match start

Runs once, 1–2s after game start.

```xs
rule llTerrainCensus
highFrequency
minInterval 1
active
{
   if (xsGetTime() < 2000) return;   // let map finish settling

   int mapSize = kbGetMapXSize();   // e.g. 480
   int step    = 24;                // 20x20 sample grid on a 480-tile map
   int cells   = (mapSize / step);

   gTerrainGridSize = cells;
   gTerrainGrid    = xsArrayCreateInt(cells * cells, 0, "terrain census");

   for (x = 0; < cells)
   {
      for (z = 0; < cells)
      {
         vector probe = cInvalidVector;
         xsVectorSet(probe, x * step, 0.0, z * step);
         int tags = llClassifyProbe(probe);
         xsArraySetInt(gTerrainGrid, x * cells + z, tags);
      }
   }

   llLogTerrainHistogram();   // probe dump for tuning
   xsDisableSelf();
}

int llClassifyProbe(vector pos = cInvalidVector)
{
   int tags = 0;

   // Coast: this tile is land, but a water group is within 15 tiles
   int hereGroup  = kbAreaGroupGetIDByPosition(pos);
   bool isLand    = kbAreaGroupIsLand(hereGroup);      // verify API name
   if (isLand && llWaterWithin(pos, 15.0)) tags |= cTerrainCoast;

   // Rivers: narrow water strip (water within 6 tiles but large water body > 30 tiles)
   if (isLand && llWaterWithin(pos, 6.0) && !llWaterWithin(pos, 30.0)) tags |= cTerrainRivers;

   // Forests: tree count > threshold in 12 radius
   if (kbUnitCount(0, cUnitTypeTree, cUnitStateAlive) > 0)
   {
      int treesNear = llCountUnitsNear(cUnitTypeTree, pos, 12.0);
      if (treesNear >= 20) tags |= cTerrainForests;
   }

   // Plains: no forest, no cliff, no water within 10
   if ((tags & (cTerrainForests | cTerrainCoast | cTerrainRivers)) == 0)
      tags |= cTerrainPlains;

   // Mountains: cliff units within 12 (AoE3 cliffs are unit-typed)
   if (llCountUnitsNear(cUnitTypeCliff, pos, 12.0) >= 3) tags |= cTerrainMountains;

   // Chokepoints: narrow passable strip between two large impassable groups
   if (llIsChokepoint(pos)) tags |= cTerrainChokepoints;

   return tags;
}
```

**Why a grid, not per-building queries:** a terrain census is one-time work. Per-building queries would re-sample every time we shadow a barracks. 400 probes at game start vs. thousands over a 40-minute match.

**Verification items before coding:** `kbAreaGroupIsLand`, `cUnitTypeCliff` — confirm these exist in DE. If cliffs don't exist as unit types in DE, use `cMountainType` or derive via passability deltas.

## 7. Scout-first TC siting

Applies to **expansion TCs** (covered wagons, forward-base TCs), NOT the starting TC.

### 7a. For the starting TC
We can't move it. Instead:

```xs
rule llAssessStartingTerrain
active
minInterval 2
{
   vector start = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
   int tags = llGetTerrainTagsAt(start);

   // Which of our prefs did the map hand us?
   int matched = tags & (gMyTerrainPref1 | gMyTerrainPref2);

   if (matched != 0)
   {
      gStartingTerrainMatch = matched;      // great — build identity-true
   }
   else
   {
      gStartingTerrainMatch = 0;
      // Fallback: degrade to generic placement for core buildings,
      // but still prefer matched terrain when expansion happens
   }

   llProbe("terrain.start", "civ=" + civ + " pref1=" + gMyTerrainPref1 +
           " pref2=" + gMyTerrainPref2 + " got=" + tags + " matched=" + matched);
   xsDisableSelf();
}
```

Result: even if the map drops a Dutch TC in the middle of plains, we know it's a mismatch and we'll pull expansions hard toward any water we find. Ethiopian TC on flat ground? We pull the military core toward any elevation and accept an imperfect start.

### 7b. For expansion TCs — the scout pass

```xs
rule llScoutForTC
minInterval 10
active
{
   // Only fire when we have queued intent to build an expansion TC
   if (!llWantsExpansionTC()) return;

   int explorerID = aiGetFallenExplorerID() >= 0 ? -1 : kbGetExplorerUnitID();
   if (explorerID < 0) return;

   // 1. Generate candidate positions: forward arc of main base, at 60-150 tile radius
   static vector[] candidates = llGenerateCandidateArc(mainBase, 60.0, 150.0, 12);

   // 2. Score each candidate by terrain affinity + safety + resource proximity
   float bestScore = -999.0;
   vector bestPos  = cInvalidVector;
   for (i = 0; < 12)
   {
      vector cand = xsArrayGetVector(candidates, i);
      float score = llScoreTCSite(cand);
      if (score > bestScore) { bestScore = score; bestPos = cand; }
   }

   // 3. Send scout to verify top candidate — reveal fog, check enemy proximity
   if (bestScore > cTCSiteAcceptThreshold)
   {
      llDispatchExplorerTo(bestPos);
      gPendingTCSite = bestPos;
      xsEnableRule("llConfirmTCSite");
   }
   else
   {
      // No good terrain — delay, re-census, or fall back to default forward vector
      gNoGoodTCSiteTries++;
      if (gNoGoodTCSiteTries > 3) llFallbackTCPlacement();
   }
}

float llScoreTCSite(vector pos = cInvalidVector)
{
   int tags = llGetTerrainTagsAt(pos);

   float terrainScore = 0.0;
   if (tags & gMyTerrainPref1) terrainScore += 1.0;
   if (tags & gMyTerrainPref2) terrainScore += 0.5;

   float safetyScore = llGetSafetyScore(pos);     // distance from enemy
   float resourceScore = llGetResourceScore(pos); // woodline + hunts + mines within 40
   float reachScore = llGetReachScore(pos);       // passable connection to main base

   return 2.0 * terrainScore + 1.5 * safetyScore + 1.0 * resourceScore + 1.0 * reachScore;
}
```

**Scout behavior:** we don't interrupt the explorer's existing scouting loop with a completely new plan — we piggyback. The explorer already roams; we just push it toward the `bestPos` when we have a candidate. If after ~45s the site is confirmed safe and terrain-tags match, we commit the TC build plan there.

**Fallback:** if the scout is dead, the best candidate is hostile, or no candidate scores above threshold, we use today's forward-vector placement. No regression.

## 8. Per-building placement affinity

Not every building cares about terrain equally. Here's the matrix — weights per building × terrain type. Multiplied by civ preference to get final score.

Weight legend: `+` = prefer, `-` = avoid, `·` = neutral, `!` = strong prefer (overrides).

| Building | Coast | Rivers | Forests | Plains | Mountains | Chokepoints |
|---|---|---|---|---|---|---|
| Town Center (expansion) | + | + | · | · | + | + |
| House / Manor | · | · | · | + | · | · |
| Mill / Farm | · | + | - | + | · | · |
| Plantation | · | + | · | + | · | · |
| Market | · | + | · | + | · | + |
| Barracks | · | · | · | + | · | · |
| Stable | - | · | - | ! | · | · |
| Artillery Foundry | · | · | · | + | + | · |
| Outpost / Tower | + | · | + | · | ! | ! |
| Fort / Castle | · | · | · | · | ! | ! |
| Dock | ! | ! | · | · | · | · |
| Church / Mosque / Shrine | · | + | + | + | + | · |
| Wonder | · | + | · | + | + | · |
| Trading Post | · | + | · | + | · | ! |

**Final score per candidate tile = base_weight[building][terrain] × civ_preference_multiplier[civ][terrain] × situational modifier.**

Example: Japanese Barracks on mountain tile.
- Base weight: `·` (0.0) for Barracks × Mountains
- Civ pref mult: 1.5 (Japanese pref1 = Mountains)
- Situational: +0.2 if elevation provides defensive bonus
- Combined score: (0.0 × 1.5) + 0.2 = 0.2

Example: Japanese Barracks on plains tile.
- Base weight: `+` (+1.0) for Barracks × Plains
- Civ pref mult: 0.3 (Plains not in Japan prefs)
- Combined: 1.0 × 0.3 = 0.3

Japanese barracks ends up with similar score on both — slight edge to plains. But a Japanese Fort? Base weight `!` (+2.0) × civ mult 1.5 on mountains = 3.0. Plains fort = +0.0 × 0.3 = 0.0. Huge divergence — Japanese forts always go on heights.

This matrix lives in a single 2D array `gBuildingTerrainWeights[cNumBuildingTypes][cNumTerrainTypes]`. Civ multiplier vector `gCivTerrainMultipliers[cNumTerrainTypes]` set once at init from the character axis table.

## 9. Spend archetypes — replace UNHANDLED

Replaces the `UNHANDLED EXCESS RESOURCES` warning branch in `aiEconomy.xs` line 470.

```xs
bool llSpendSurplusByArchetype(void)
{
   float food = kbResourceGet(cResourceFood);
   float wood = kbResourceGet(cResourceWood);
   float gold = kbResourceGet(cResourceGold);

   if (gMySpendArchetype == cSpendWarmaker)
   {
      // Bump maintain counts on active military plans by +5 (capped at 2x base)
      llBumpMaintainPlans(5, 2.0);
      // Queue extra barracks/stable if military building count low
      if (gold > 1500.0 && llMilitaryBuildingCount() < kbGetPop() / 15)
         llQueueMilitaryBuilding();
      return true;
   }
   else if (gMySpendArchetype == cSpendMercantilist)
   {
      // Market trade: convert surplus of one into deficit of another
      if (food > 2500.0 && gold < 500.0) aiCommerceSetSell(cResourceFood, 0.5);
      else if (wood > 2500.0 && gold < 500.0) aiCommerceSetSell(cResourceWood, 0.5);
      // Prioritize trade-post shipments if deck allows
      llBoostTradePostPriority();
      return true;
   }
   else if (gMySpendArchetype == cSpendMonumentalist)
   {
      // Queue wonder if not built; else expensive tech; else extra house/church
      if (!llHasWonderBuilt() && kbGetAge() >= cAge3) llQueueWonder();
      else if (gold > 2000.0) llQueueExpensiveTech();
      return true;
   }
   else if (gMySpendArchetype == cSpendReinvestor)
   {
      // More production buildings + tech upgrades + villager cap expansion
      if (wood > 1500.0) llQueueProductionBuilding();
      if (gold > 1500.0) llQueueNextEligibleTech();
      return true;
   }
   else if (gMySpendArchetype == cSpendStockpiler)
   {
      // Actually keep reserves higher — raise the anti-hoard threshold from 1500 to 2500
      gStockpilerMode = true;
      return false;   // let resources accumulate (Inca qollqa)
   }
   else if (gMySpendArchetype == cSpendSubsistence)
   {
      // Low maintain counts, raid more
      llSetLowMaintainMode();
      llBoostRaidPriority();
      return true;
   }
   return false;
}
```

Called from `handleExcessResources()` as the new Age ≥ 3 branch replacing the warning.

## 10. Integration architecture

```
 ┌──────────────────────────────────────────────────────┐
 │           aiCharacterAxes.xs  (NEW)                  │
 │  llInitCharacterAxes()  →  sets gMy* globals         │
 │  llGetTerrainTagsAt()   →  O(1) grid lookup          │
 │  gBuildingTerrainWeights[][]  (matrix literal)       │
 │  gCivTerrainMultipliers[]     (init from civ)        │
 └─────────────┬────────────────────────────────────────┘
               │ read by
               ▼
 ┌─────────────────────────┐ ┌─────────────────────────┐
 │  aiTerrainCensus.xs     │ │  aiPlacement.xs (hook)  │
 │  (NEW) — grid builder   │ │  llScoreSite() called   │
 │  llTerrainCensus rule   │ │  before aiPlanCreate    │
 └─────────────────────────┘ │  for every build plan   │
                             └─────────┬───────────────┘
                                       │
 ┌─────────────────────────────────────┼───────────────┐
 │  aiBuildings.xs / aiBuildingsWalls.xs/ aiEconomy.xs │
 │  — existing files gain thin call sites that ask     │
 │    the character system for site-score, spend-     │
 │    archetype behavior, wall archetype.              │
 └─────────────────────────────────────────────────────┘
```

Existing files gain **call sites**, not reimplementations. Each of the ~225 civ-specific branches can be audited later and consolidated into character-axis reads, but phase 1 leaves them alone.

## 11. Rollout phases

**Phase 1 — Scaffolding (no behavior change yet).** ~1 day.
- Create `aiCharacterAxes.xs`, populate for all 23 civs from the character axis table.
- Create `aiTerrainCensus.xs` with one-shot grid builder and `llGetTerrainTagsAt` helper.
- Probe-log `terrain.start` and `terrain.histogram` to verify classification works on real maps.
- **No behavior changes.** Just instrumentation.

**Phase 2 — Fix wall mismatches + spend archetypes.** ~1 day.
- Apply the 5 wall doctrine corrections (with owner confirmation).
- Wire `llSpendSurplusByArchetype()` into `handleExcessResources` for Age ≥ 3.
- Keep `UNHANDLED` warning as fallback for archetypes not yet implemented.

**Phase 3 — TC siting (the headline feature).** ~2 days.
- Scout-first expansion TC placement via `llScoreTCSite` + scout dispatch.
- Starting TC terrain assessment + fallback mode.
- Probe-log `tc.score`, `tc.commit`, `tc.fallback` for every placement decision.

**Phase 4 — Per-building terrain affinity.** ~2–3 days.
- Building × terrain weight matrix.
- Replace site selection inside all `aiPlanCreate(cPlanBuild, ...)` call sites with `llPickTerrainAwareSite(buildingType)`.
- Regression-test every civ on standard maps (Great Plains, Saguenay, Yukon, Pampas Sierras, Himalayas).

**Phase 5 — Labor bias + audit consolidation.** ~2 days.
- Translate the Labor Bias column into per-civ villager allocation tweaks (fishing civs get more fishermen, hunt civs get more hunt-focused gathering).
- Audit the 225 scattered civ-specific branches; collapse duplicates into character-axis reads.

Total: 8–10 engineer-days for the full broad scope.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Terrain census mis-classifies on unusual maps (e.g., Arctic Region, Sea of Japan) | Probe-log histograms + adjust thresholds per map-size bucket |
| Scout dies before expansion TC placement | Fallback to today's forward-vector placement (no regression) |
| Per-building matrix creates unbuildable towns (everything wants same tile) | Add diversity penalty — score decays near existing same-type buildings |
| Archetype spending over-trains military or over-builds wonders | Per-archetype caps (+50% maintain, max 1 wonder, etc.) + probe-log every decision |
| Revolution civs don't have entries in character-axes table | `llNormalizeCivName` already handles them; default to parent civ's axes |
| Water-group tag classifier confuses rivers vs. lakes | Calibrate thresholds using the terrain histogram probe output on known-river maps (Orinoco, Amazonia) |

## 13. Open questions for owner review

1. **Wall mismatch flips** — confirm the 5 corrections are desired. Hiawatha/Tokugawa/Shivaji being MobileNoWalls looks like oversight, but you may have narrative reasons.
2. **Garibaldi** — keep UrbanBarricade (Italian republican civic-militia flavor, defensible design) or flip to FortressRing (historical trace italienne)?
3. **Starting TC tolerance** — if map terrain clashes hard with civ identity (Dutch on a landlocked map), do we (a) play degraded identity, (b) race to expand to water ASAP, or (c) spam markets to simulate trade-focus? My default is (b) with (a) as fallback.
4. **Chokepoint civs on chokepoint-sparse maps** — Hausa on Great Plains, Maltese on Saguenay. Default to terrain pref 1 or synthesize chokepoint behavior via defensive clustering?
5. **Probe dump appetite** — we'll emit a lot of new probes (`terrain.*`, `tc.*`, `spend.*`). OK to log liberally during Phase 1–3 and tighten later?

## 14. Artifact summary

This note is the design source of truth. When we implement, the character axis table (section 4) becomes `aiCharacterAxes.xs`. The building matrix (section 8) becomes a literal 2D array. The spend archetypes (section 9) become a switch block. The terrain census (section 6) becomes a one-shot rule.

Everything else in the AI reads from these four artifacts. No new civ-specific branches are added during implementation — the axis table is the knob.

---

**Next step:** review and approve this doc (or request changes), then kick off Phase 1.
