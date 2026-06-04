# AI Knob Inventory — Complete Reference

**Status:** Source of truth for per-nation tuning + radar-chart visualization
**Scope:** Every configurable variable in the A New World AI mod
**Total:** ~165 knobs across 12 categories
**Date:** 2026-04-24

---

## How to read this document

| Column | Meaning |
|---|---|
| **Type** | float / int / bool / const / vector / plan-id / array |
| **Min / Max** | Hard bounds. `—` = unbounded in code. Bools → `false/true`. |
| **Default** | Value if not set by leader init |
| **Description** | What it controls + behavioral effect |
| **File:Line** | Where defined (most are declared in `aiHeader.xs` or `aiGlobals.xs`) |

Categories:

- [A. Behavior Traits (bt*)](#a-behavior-traits-bt) — 7 knobs, personality sliders
- [B. Permission Gates (cv*Ok*)](#b-permission-gates-cvok) — 20 knobs, binary capability flags
- [C. Limits (cvMax* / cvMin*)](#c-limits-cvmax--cvmin) — 5 knobs, hard caps
- [D. Military/Tactical (cvPrimary*, cvDefense*)](#d-militarytactical) — 8 knobs
- [E. Build Style + Wall Strategy (cLLBuildStyle*, gLL*)](#e-build-style--wall-strategy) — 30 knobs
- [F. Elite Tactical Doctrine (gLLExplorer*)](#f-elite-tactical-doctrine) — 4 knobs
- [G. Engine Setters (ai*Set*)](#g-engine-setters) — 45+ functions
- [H. Resource/Economy Arrays](#h-resourceeconomy-arrays) — 6 arrays
- [I. Maintain Plans (g*Maintain)](#i-maintain-plans) — 12 plan handles
- [J. Naval (gNavy*, gWater*)](#j-naval) — 13 knobs
- [K. Difficulty + Map](#k-difficulty--map) — 6 knobs
- [L. Exploration](#l-exploration) — 6 knobs
- [M. Leader Helper Functions](#m-leader-helper-functions) — 9 helpers
- [N. Rule Intervals](#n-rule-intervals) — 25+ cadence values

---

## A. Behavior Traits (bt*)

Declared in `aiHeader.xs:45–118`. Floats on **[-1.0, +1.0]**. Positive emphasizes first descriptor, negative the second.

| Knob | Type | Min | Max | Default | Description |
|---|---|---|---|---|---|
| `btRushBoom` | float | -1.0 | +1.0 | 0.0 | Positive rushes early, skips economy upgrades; negative booms, more banks/markets. `<= -0.5` raises Fortress population cap |
| `btOffenseDefense` | float | -1.0 | +1.0 | 0.0 | Positive sends Fort Wagons forward on moderate+ difficulty; negative adds early towers and reverses Fort Wagon deck priority |
| `btBiasNative` | float | -1.0 | +1.0 | 0.0 | `>= 0.5`: faster Native TP chain, more minor-civ troops, native cards priority-in. `< -0.5`: fewer native cards |
| `btBiasTrade` | float | -1.0 | +1.0 | 0.0 | `>= 0.5`: Trade Route TP priority, trade-card deck weight. `< -0.5`: trade cards deprioritized |
| `btBiasCav` | float | -1.0 | +1.0 | 0.0 | Unit-picker priority: `result + 0.5 + (btBiasCav/2.0)`. `-1.0` exempts cavalry entirely |
| `btBiasArt` | float | -1.0 | +1.0 | 0.0 | Unit-picker priority: `result + 0.5 + (btBiasArt/2.0)`. `-1.0` exempts artillery entirely |
| `btBiasInf` | float | -1.0 | +1.0 | 0.0 | Unit-picker priority: `result + 0.5 + (btBiasInf/2.0)`. `-1.0` exempts infantry entirely |

## B. Permission Gates (cv*Ok*)

Declared in `aiHeader.xs:126–155`. Mostly **write-once in preInit()** — some are dynamic mid-game (noted).

| Knob | Type | Default | Dynamic? | Description |
|---|---|---|---|---|
| `cvInactiveAI` | bool | false | No | `true`: only micro existing units; no planning/building/training |
| `cvOkToAttack` | bool | true | No | `false`: no land/water attacks, no ally defense |
| `gDelayAttacks` | bool | false | No | Standard difficulty: block attacks until attacked or Industrial reached |
| `cvOkToTrainArmy` | bool | true | No | `false`: no military training (shipment units still come) |
| `cvOkToTrainNavy` | bool | true | No | `false`: no naval training |
| `cvOkToTaunt` | bool | true | No | `false`: suppress ambient chats (SPC default) |
| `cvOkToAllyNatives` | bool | true | No | `false`: no Native Settlement TPs |
| `cvOkToClaimTrade` | bool | true | No | `false`: no Trade Route TPs |
| `cvOkToBuild` | bool | true | No | `false`: no buildings or wagons at all |
| `cvOkToFortify` | bool | true | No | `false`: no towers/outposts/war huts/castles |
| `cvOkToBuildForts` | bool | true | No | `false`: no Fort Wagons. Paired with `cvOkToFortify=false`: no Strongholds |
| `cvOkToBuildConsulate` | bool | true | **Yes** | `false`: Asian Consulate suppressed |
| `cvOkToResign` | bool | true | No | `false`: never surrender |
| `cvOkToExplore` | bool | true | No | `false`: all explore plans off |
| `cvOkToFish` | bool | true | No | `false`: no docks, no fishing boats. Requires map flagged `AIFishingUseful` |
| `cvOkToGatherFood` | bool | true | **Yes** | `false`: food gathering off |
| `cvOkToGatherGold` | bool | true | **Yes** | `false`: gold gathering off |
| `cvOkToGatherWood` | bool | true | **Yes** | `false`: wood gathering off |
| `cvOkToGatherNuggets` | bool | true | No | `false`: explorer ignores treasures |
| `cvOkToBuildDeck` | bool | false | No | Auto-true in RM. `false`: no deck assembly |

**Deprecated (no-ops, keep for compat):** `cvOkToSelectMissions`, `cvOkToChat`, `cvDoAutoSaves`, `cvOkToBuildWalls`.

## C. Limits (cvMax* / cvMin*)

Declared in `aiHeader.xs:157–162`. Use `-1` to let the AI decide; `0` to disable entirely.

| Knob | Type | Min | Max | Default | Description |
|---|---|---|---|---|---|
| `cvMaxArmyPop` | int | 0 | — | -1 | Hard cap on military pop. `-1`: AI decides. `0`: no army |
| `cvMaxCivPop` | int | 0 | — | -1 | Hard cap on settler pop. Changes after `cvMaxAge` reached are ignored |
| `cvMaxAge` | int | cAge1 | cAge5 | cAge5 | Ceiling age. Set to cAge2..cAge4 to cap progression |
| `cvMaxTowers` | int | 0 | — | -1 | Target tower count. `-1`: AI decides. `0`: no towers |
| `cvMinNumVills` | int | 0 | — | -1 | Floor before diverting to military. `-1`: AI decides |

## D. Military/Tactical

Unit selection + defensive reflex radii. Declared in `aiHeader.xs:164–178`.

| Knob | Type | Min | Max | Default | Description |
|---|---|---|---|---|---|
| `cvPrimaryArmyUnit` | int | proto ID | — | -1 | Force primary unit type. `-1`: AI chooses |
| `cvSecondaryArmyUnit` | int | proto ID | — | -1 | Only used if `cvNumArmyUnitTypes > 2` |
| `cvTertiaryArmyUnit` | int | proto ID | — | -1 | Only used if `cvNumArmyUnitTypes > 3` |
| `cvNumArmyUnitTypes` | int | 1 | 3+ | -1 | Limit unit-type variety |
| `cvPlayerToAttack` | int | player ID | — | -1 | Focus one enemy only |
| `cvDefenseReflexRadiusActive` | float | 0.0 | — | 60.0 | Defense engagement range (meters) |
| `cvDefenseReflexRadiusPassive` | float | 0.0 | — | 30.0 | Defense engagement when regrouping |
| `cvDefenseReflexSearchRadius` | float | 0.0 | `RadiusActive` | 60.0 | Detection range. MUST NOT exceed RadiusActive |

## E. Build Style + Wall Strategy

LL-namespace globals in `aiHeader.xs:180–218`. Usually set via `llUseXxxStyle()` wrappers.

### Build-style selection

| Knob | Type | Min | Max | Default | Description |
|---|---|---|---|---|---|
| `gLLBuildStyle` | int | 0 | 14 | 0 | Active preset (see 14 `cLLBuildStyle*` constants below) |
| `gLLWallLevel` | int | 0 | 5 | 1 | Wall tier. 0=no walls, 1=palisade, 3=stone, 5=max (Valette) |
| `gLLEarlyWallingEnabled` | bool | — | — | true | Age 1 walling allowed |
| `gLLLateWallingEnabled` | bool | — | — | true | Age 3+ walling allowed |
| `gLLWallStrategy` | int | 0 | 5 | 0 | Active archetype (see 6 `cLLWallStrategy*` below) |

### Build-style constants (14 presets)

| Constant | Value | Distance mults (house/econ/mil/tc) | Tower/Fort/ForwardTower | Characteristic |
|---|---|---|---|---|
| `cLLBuildStyleCompactFortifiedCore` | 1 | 0.75 / 0.85 / 0.85 / 0.85 | 3 / 2 / 2 | Tight Vauban fortress |
| `cLLBuildStyleDistributedEconomicNetwork` | 2 | 1.15 / 1.35 / 1.00 / 1.35 | 1 / 1 / 1 | Scattered frontier |
| `cLLBuildStyleForwardOperationalLine` | 3 | 1.00 / 1.05 / 0.95 / 1.10 | 1 / 2 / 3 | Napoleon manoeuvre |
| `cLLBuildStyleMobileFrontierScatter` | 4 | 1.35 / 1.45 / 1.10 / 1.50 | 1 / 0 / 1 | Plains mobile |
| `cLLBuildStyleShrineTradeNodeSpread` | 5 | 1.00 / 1.50 / 0.95 / 1.20 | 1 / 1 / 1 | Sakoku redoubts |
| `cLLBuildStyleCivicMilitiaCenter` | 6 | 0.95 / 1.05 / 0.95 / 1.15 | 2 / 1 / 2 | Washington frontier |
| `cLLBuildStyleSteppeCavalryWedge` | 7 | 1.40 / 1.50 / 1.15 / 1.55 | 1 / 0 / 1 | Hussar raiders |
| `cLLBuildStyleNavalMercantileCompound` | 8 | 1.10 / 1.30 / 1.00 / 1.25 | 2 / 2 / 1 | Maurice / Wellington |
| `cLLBuildStyleSiegeTrainConcentration` | 9 | 0.90 / 1.00 / 0.85 / 0.95 | 2 / 2 / 3 | Frederick Prussian |
| `cLLBuildStyleJungleGuerrillaNetwork` | 10 | 1.10 / 1.30 / 0.95 / 1.30 | 1 / 0 / 2 | Maya / Aztec |
| `cLLBuildStyleHighlandCitadel` | 11 | 0.65 / 0.90 / 0.80 / 0.70 | 4 / 3 / 2 | Valette / Menelik |
| `cLLBuildStyleCossackVoisko` | 12 | 0.90 / 1.00 / 0.80 / 0.95 | 2 / 2 / 3 | Catherine kremlin |
| `cLLBuildStyleRepublicanLevee` | 13 | 0.95 / 1.05 / 0.90 / 1.10 | 2 / 1 / 3 | Robespierre / Garibaldi |
| `cLLBuildStyleAndeanTerraceFortress` | 14 | 0.80 / 0.95 / 0.90 / 0.90 | 3 / 2 / 2 | Pachacuti terraces |

### Wall strategy constants (6 archetypes)

| Constant | Value | Placement logic |
|---|---|---|
| `cLLWallStrategyFortressRing` | 0 | Full 360° ring, symmetric, 6–18 gates by age |
| `cLLWallStrategyChokepointSegments` | 1 | Walls only at terrain pinches |
| `cLLWallStrategyCoastalBatteries` | 2 | Land ring + coastal gun towers |
| `cLLWallStrategyFrontierPalisades` | 3 | Quick wooden ring + blockhouses |
| `cLLWallStrategyUrbanBarricade` | 4 | Tight inner ring + urban towers |
| `cLLWallStrategyMobileNoWalls` | 5 | No walls; scouts + outposts only |

### Distance multipliers (runtime-tunable per civ)

| Knob | Type | Min | Max | Default | Description |
|---|---|---|---|---|---|
| `gLLHouseDistanceMultiplier` | float | 0.5 | 1.5 | 1.0 | House spread. <1: tight; >1: sprawl |
| `gLLEconomicDistanceMultiplier` | float | 0.5 | 1.5 | 1.0 | Mill/plantation/dock spread |
| `gLLMilitaryDistanceMultiplier` | float | 0.5 | 1.5 | 1.0 | Barracks/stable spread |
| `gLLTownCenterDistanceMultiplier` | float | 0.5 | 1.5 | 1.0 | Secondary TC spread |
| `gLLTowerLevel` | int | 0 | 4 | 1 | Tower build cadence per age |
| `gLLFortLevel` | int | 0 | 3 | 1 | Fort wagon cadence |
| `gLLForwardBaseTowerCount` | int | 1 | 3 | 2 | Towers per forward operating base |
| `gLLPreferForwardFortifiedBase` | bool | — | — | false | `true`: prefer 2 forts (1 forward) at Age 4+ |

### Identity strings (telemetry only)

| Knob | Type | Description |
|---|---|---|
| `gLLLeaderKey` | string | Leader module key (for replay probes) |
| `gLLChatsetKey` | string | Chat portrait / quote routing key |

## F. Elite Tactical Doctrine

Set via `llSetLeaderTacticalDoctrine(protect, decap, escort, rearOffset)`. Declared in `aiEliteTactics.xs:19–22`.

| Knob | Type | Min | Max | Default | Description |
|---|---|---|---|---|---|
| `gLLExplorerProtectionOverride` | float | -1.0 | 1.0 | -1.0 | Override auto-calc. `-1.0`: use formula. Otherwise clamped to [0,1] |
| `gLLDecapitationOverride` | float | -1.0 | 1.0 | -1.0 | Enemy-explorer-hunt bias override |
| `gLLExplorerEscortBonus` | int | 0 | — | 0 | Extra escort units for explorer |
| `gLLExplorerRearOffsetBonus` | float | 0.0 | — | 0.0 | Extra rear-offset for leader positioning |

**Auto-calc formula** (if overrides = -1.0):
```
protection = 0.55 - (btOffenseDefense * 0.35) + (btBiasInf * 0.12)
             + (btBiasArt * 0.10) - (btBiasCav * 0.14) - (btBiasNative * 0.06)
decapitation = 0.20 + (btOffenseDefense * 0.38) + (btBiasCav * 0.15)
              + (btBiasNative * 0.08) - (btBiasInf * 0.05) - (btBiasArt * 0.05)
```

## G. Engine Setters

`ai*Set*` functions that configure AI behavior at runtime (or from rules). Not exhaustive — just the commonly used ones.

### Population & economy

| Function | Range | Description |
|---|---|---|
| `aiSetEconomyPop(int pop)` | 0–200 | Target settler count |
| `aiSetMilitaryPop(int pop)` | 0–200 | Military pop cap |
| `aiSetEconomyPercentage(float pct)` | 0.0–1.0 | Economy focus weighting |
| `aiSetMilitaryPercentage(float pct)` | 0.0–1.0 | Military focus weighting |
| `setMilPopLimit(a1, a2, a3, a4, a5)` | 0–200 each | Per-age military pop ramp (wrapper) |

### Resource allocation

| Function | Range | Description |
|---|---|---|
| `aiSetResourcePercentage(res, market, pct)` | 0.0–1.0 | Allocate % gatherers or market to resource |
| `aiSetResourceBreakdown(res, subtype, plans, prio, eff, base)` | varies | Detailed per-source allocation (Hunt/Fish/Farm/Mine) |
| `aiSetResourceGathererPercentageWeight(src, weight)` | 0.0–1.0 | Blend script-driven vs. cost-driven dispatch |
| `aiSetReservedGatherRate(res, rate)` | 0.0–1.0 | Portion reserved for non-gather uses (shipments) |

### Market/commerce

| Function | Range | Description |
|---|---|---|
| `aiCommerceSetSell(res, pct)` | 0.0–1.0 | Market sell percentage for resource |
| `aiCommerceSetBuy(res, pct)` | 0.0–1.0 | Market buy allocation for resource |

### Military direction

| Function | Range | Description |
|---|---|---|
| `aiSetMostHatedPlayerID(pid)` | player ID | Target hatred at specific enemy |
| `aiSetExploreDangerThreshold(t)` | 0.0–100+ | Explorer retreat threshold |

### Planning

| Function | Range | Description |
|---|---|---|
| `aiPlanSetDesiredPriority(id, prio)` | 0–100 | Execution priority |
| `aiPlanSetDesiredResourcePriority(id, prio)` | 0–100 | Resource-claim priority |
| `aiPlanSetActive(id, bool)` | — | Enable/disable plan |
| `aiPlanSetEscrowID(id, escrow)` | `cEconomyEscrowID` etc. | Resource pool binding |
| `aiPlanSetBaseID(id, baseID)` | — | Anchor plan to base |
| `aiPlanSetVariableInt/Float/Vector/Bool/String(id, var, idx, val)` | varies | Set plan variable |
| `aiPlanAddUnitType(id, unit, min, desired, max)` | — | Add unit type to train/combat plan |
| `aiPlanAddUnit(id, unitID)` | — | Assign specific unit |
| `aiPlanSetNoMoreUnits(id, bool)` | — | Lock unit list |

### Home city / cards

| Function | Range | Description |
|---|---|---|
| `aiHCDeckActivate(deckIdx)` | — | Activate a deck |
| `aiHCDeckPlayCard(deckIdx, cardIdx)` | — | Send a shipment |
| `addCardToDeck(deckIdx, cardIdx)` | — | Add card during assembly |

### Unit picker

| Function | Range | Description |
|---|---|---|
| `kbUnitPickSetPreferenceFactor(id, unit, factor)` | -1.0 to 1.0 | Bias picker; -1.0 exempts unit |
| `kbUnitPickSetMinimumNumberUnits(id, n)` | int | Floor unit count |
| `kbUnitPickSetMaximumNumberUnits(id, n)` | int | Cap unit count |

### Escrows

| Function | Range | Description |
|---|---|---|
| `aiSetEscrowsDisabled(bool)` | — | Disable all escrows (manual control) |
| `aiSetPlanResourcePriorityEnabled(id, bool)` | — | Toggle resource prio on plan |

## H. Resource/Economy Arrays

| Array | Indexed by | Values | Range | Description |
|---|---|---|---|---|
| `gTargetSettlerCounts` | cAge1..cAge5 | int | 10–80 | Settlers per age. Difficulty-scaled. Standard: 15/25/25/25/25 → Expert: 15/45/80/80/80 |
| `gTargetSettlerCountsDefault` | cAge1..cAge5 | int | — | Non-special baseline |
| `gResourceNeeds` | food/wood/gold | float | — | Current deficit (+) or excess (-) |
| `gExtraResourceNeeds` | food/wood/gold | float | — | Extra demand for market conversions |
| `gRawResourcePercentages` | food/wood/gold | float | 0.0–1.0 | Pre-market allocation. Sums to 1.0 |
| `gMarketBuySellPercentages` | [4] | float | 0.0–1.0 | [BuyFoodWithGold, BuyWoodWithGold, SellFoodForGold, SellWoodForGold] |

## I. Maintain Plans

Plan-ID handles for standing unit orders. Set unit count via `aiPlanSetVariableInt(planID, cTrainPlanNumberToMaintain, 0, N)`.

| Plan Global | Purpose |
|---|---|
| `gSettlerMaintainPlan` | Main villager training |
| `gMaxInfantryMaintain` | Infantry continuous |
| `gMaxCavalryMaintain` | Cavalry continuous |
| `gArtilleryMaintain` | Artillery continuous |
| `gMaxVillagersMaintain` | Settler pop control |
| `gNativeScoutLimit` | Native scout units |
| `gCaravelMaintain` | Caravel ships |
| `gGalleonMaintain` | Galleon ships |
| `gFrigateMaintain` | Frigate ships |
| `gMonitorMaintain` | Monitor ships |
| `gBattleshipMaintain` | Battleship |
| `gWaterExploreMaintain` | Water explorer |

## J. Naval

| Knob | Type | Description |
|---|---|---|
| `gNavyVec` | vector | Center of naval operations |
| `gWaterMap` | bool | Is map water-heavy? |
| `gNavyMap` | bool | Are naval ops enabled overall? |
| `gNetNavyValue` | float | Naval power-balance score |
| `gHaveWaterSpawnFlag` | bool | Water spawn exists |
| `gWaterSpawnFlagID` | int | Water spawn unit ID |
| `gFishingUnit` | int | Fishing boat proto ID |
| `gCaravelUnit` | int | Caravel proto ID |
| `gGalleonUnit` | int | Galleon proto ID |
| `gFrigateUnit` | int | Frigate proto ID |
| `gMonitorUnit` | int | Monitor proto ID |
| `gBattleShipUnit` | int | Battleship proto ID |
| `gTransportUnit` | int | Transport ship proto ID |

## K. Difficulty + Map

| Knob | Type | Values | Description |
|---|---|---|---|
| `cDifficultyCurrent` | const int | Sandbox/Easy/Moderate/Hard/Expert | Read-only |
| `gDifficultyExpert` | int | — | Threshold used by hard-mode branches |
| `gAssumedWaterMap` | bool | — | Map bias toward water |
| `gIsArchipelago` | bool | — | Archipelago rules engaged |
| `gIsKingOfTheHill` | bool | — | KOTH rules engaged |
| `gTreasureMap` | bool | — | Map has treasure density |
| `gMapSizeID` | int | — | Small/Medium/Large ID |
| `gMapName` | string | — | Map display name |

## L. Exploration

| Knob | Type | Description |
|---|---|---|
| `gLandExplorePlan` | int | Plan ID for land exploration |
| `gWaterExplorePlan` | int | Plan ID for water exploration |
| `gExplorerControlPlan` | int | Plan ID for explorer positioning |
| `gIslandMap` | bool | Scattered-island layout detected |
| `cvOkToExplore` | bool | Master enable (see Section B) |
| `cvOkToGatherNuggets` | bool | Treasure hunting enable (see Section B) |

## M. Leader Helper Functions

Called in `initLeader*()`. Wrap multiple knob writes into one doctrinal command.

| Function | Effect |
|---|---|
| `llSetDefensivePersonality()` | Resets bt*, sets `btRushBoom=-0.4`, `btOffenseDefense=-0.6` |
| `llSetBalancedPersonality()` | Resets bt* to neutral |
| `llSetMilitaryFocus(inf, cav, art)` | Sets `btBiasInf/Cav/Art` |
| `llEnableForwardBaseStyle()` | `btOffenseDefense=1.0`, `cvDefenseReflexRadius*=75.0` |
| `llEnableDeepDefenseStyle()` | `btOffenseDefense=-0.5`, `cvMaxTowers=7`, `cvDefenseReflexRadiusPassive=40.0` |
| `llUseXxxStyle(wallLevel)` | Applies one of 14 build-style presets (see Section E) |
| `llSetLeaderTacticalDoctrine(p, d, e, o)` | Sets 4 elite-tactical globals |
| `llAssignLeaderIdentity(key, chatset)` | Sets leader/chat telemetry keys |
| `llConfigureBuildStyleProfile(style, wall, early, hM, eM, mM, tcM, tL, fL, fbT, pfb)` | Low-level build-style writer |

## N. Rule Intervals

Rule `minInterval N` values (seconds). Not tunable per-civ today, but indicate reaction cadence. No global scaling factor.

| Interval | Rule examples | Category |
|---|---|---|
| 1–3s | `houseMonitor`, `delayTorpMonitor`, `tradingPostMonitor` | Fast reaction |
| 5–10s | `buildingMonitor`, `exploreMonitor`, `archipelagoGo`, `wagonMonitor` | Regular |
| 20–50s | `repairManager`, `boringChatter`, `wellingtonLongbowScreen` | Cadence |
| 60–100s | `monasteryMonitor`, `wellingtonIronDuke` | Slow monitoring |

---

## Summary table

| Category | Count | Radar-friendly? |
|---|---|---|
| A. Behavior Traits (bt*) | 7 | Yes — all scalar on [-1,+1] |
| B. Permission Gates | 20 | Partial — bools, composite them |
| C. Limits | 5 | Yes — normalize by reasonable max |
| D. Military/Tactical | 8 | Yes — mix of int and float |
| E. Build Style + Walls | 30 | Partial — 6 are categorical |
| F. Elite Tactical Doctrine | 4 | Yes |
| G. Engine Setters | 45+ | No — these are actions, not state |
| H. Resource/Econ Arrays | 6 | Derive one axis per resource |
| I. Maintain Plans | 12 | Derive via target unit counts |
| J. Naval | 13 | Partial |
| K. Difficulty + Map | 8 | No — environmental |
| L. Exploration | 6 | Partial |
| M. Leader Helpers | 9 | N/A — wrappers |
| N. Rule Intervals | 25+ | No — not per-civ |
| **Total** | **~165** | **~40 directly radar-viable, ~20 ideal for primary radar** |

---

## Radar-chart axis proposal (20 composite dimensions)

For a readable polar diagram, collapse related knobs into 20 interpretable axes, each normalized to [0, 1]:

| # | Axis | Source knob(s) | Normalization |
|---|---|---|---|
| 1 | **Boom ↔ Rush** | `btRushBoom` inverted | `(btRushBoom + 1) / 2` |
| 2 | **Offense ↔ Defense** | `btOffenseDefense` | `(btOffenseDefense + 1) / 2` |
| 3 | **Infantry Focus** | `btBiasInf` | `(btBiasInf + 1) / 2` |
| 4 | **Cavalry Focus** | `btBiasCav` | `(btBiasCav + 1) / 2` |
| 5 | **Artillery Focus** | `btBiasArt` | `(btBiasArt + 1) / 2` |
| 6 | **Trade Emphasis** | `btBiasTrade` | `(btBiasTrade + 1) / 2` |
| 7 | **Native Alliance** | `btBiasNative` | `(btBiasNative + 1) / 2` |
| 8 | **Army Ceiling** | `cvMaxArmyPop` (Age 5) | `clamp(pop / 200, 0, 1)` |
| 9 | **Villager Ceiling** | `cvMaxCivPop` | `clamp(pop / 150, 0, 1)` |
| 10 | **Tower Density** | `cvMaxTowers` (Age 4+) | `clamp(towers / 12, 0, 1)` |
| 11 | **Wall Commitment** | `gLLWallLevel` + early/late flags | `(wallLevel / 5) * (earlyOn ? 1.0 : 0.6)` |
| 12 | **Building Density** | inverse of `gLLHouseDistanceMultiplier` | `clamp((1.5 - mult) / 1.0, 0, 1)` |
| 13 | **Expansion Reach** | `gLLTownCenterDistanceMultiplier` | `clamp((mult - 0.5) / 1.0, 0, 1)` |
| 14 | **Defense Perimeter** | `cvDefenseReflexRadiusActive` | `clamp(radius / 100, 0, 1)` |
| 15 | **Forward Fortification** | `gLLPreferForwardFortifiedBase` + `gLLForwardBaseTowerCount` | `(pref ? 0.5 : 0) + (fbTowers / 6)` |
| 16 | **Fort Commitment** | `gLLFortLevel` | `fortLevel / 3` |
| 17 | **Fishing Priority** | `cvOkToFish` + starting dock rules | binary + context |
| 18 | **Explorer Protection** | derived protection bias | already [0,1] |
| 19 | **Decap Aggression** | derived decap bias | already [0,1] |
| 20 | **Settler Ramp Steepness** | `gTargetSettlerCounts` delta Age1→Age5 | `clamp((a5 - a1) / 80, 0, 1)` |

**Non-radar badges** to show alongside:
- Wall archetype (1 of 6)
- Build style (1 of 14)
- Spend archetype (1 of 6 — from character-axis table)
- Terrain preference 1 + 2 (from character-axis table)
- Military identity (one-line string)

---

## Source files

- `aiHeader.xs` — bt*, cv*, gLL* declarations
- `aiGlobals.xs` — plan handles, resource arrays, naval globals
- `aiEliteTactics.xs` — elite tactical globals
- `aiSetup.xs` — settler-count arrays, difficulty branches
- `aiEconomy.xs` — resource allocation setters, market logic
- `aiMilitary.xs` — unit picker config, attack plans
- `aiBuildings.xs` — placement logic, per-civ branches
- `aiBuildingsWalls.xs` — wall strategy dispatch
- `aiHCCards.xs` — deck assembly, card priority
- `game/ai/leaders/leaderCommon.xs` — helper functions, build-style wrappers
- `game/ai/leaders/leader_*.xs` — per-leader init + rules
