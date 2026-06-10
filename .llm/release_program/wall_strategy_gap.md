# Wall Strategy Gap — Release Audit

**Date:** 2026-06-08  
**Scope:** Read-only audit. No .xs or .py files were modified.

---

## 1. Wall Strategy Enum

Source: `/var/home/jflessenkemper/AOE-3-DE-A-New-World/game/ai/aiHeader.xs` lines 202–207.

| Value | Constant Name | One-line Meaning |
|-------|---------------|------------------|
| 0 | `cANWWallStrategyFortressRing` | Full double ring on all sides — dense perimeter |
| 1 | `cANWWallStrategyChokepointSegments` | Short wall segments placed only at terrain pinches |
| 2 | `cANWWallStrategyCoastalBatteries` | Land-side ring + gun towers facing coast, water side open |
| 3 | `cANWWallStrategyFrontierPalisades` | Quick wooden palisade ring with blockhouses, low stone |
| 4 | `cANWWallStrategyUrbanBarricade` | Tight compact inner ring + dense towers |
| 5 | `cANWWallStrategyMobileNoWalls` | No perimeter walls — scouts + outposts only |

Default global: `gANWWallStrategy = 0` (FortressRing) at aiHeader.xs line 209.

---

## 2. The 44 Canonical ANW Civ Tokens

Source: `/var/home/jflessenkemper/AOE-3-DE-A-New-World/data/civmods.xml` — all `<name>` tags with `<main>1</main>`.

```
ANWNapoleonicFrance   ANWRevFrance        ANWCanadians        ANWBrazil
ANWArgentines         ANWChileans         ANWPeruvians        ANWColumbians
ANWHaitians           ANWIndonesians      ANWSouthAfricans    ANWFinnish
ANWHungarians         ANWRomanians        ANWBarbary          ANWEgyptians
ANWMayans             ANWTexians          ANWCalifornians     ANWCentralAmericans
ANWBajaCalifornians   ANWRioGrande
ANWAztecs             ANWBritish          ANWChinese          ANWDutch
ANWEthiopians         ANWFrench           ANWGermans          ANWHaudenosaunee
ANWHausa              ANWInca             ANWIndians          ANWItalians
ANWJapanese           ANWLakota           ANWMaltese          ANWMexicans
ANWOttomans           ANWPortuguese       ANWRussians         ANWSpanish
ANWSwedes             ANWUSA
```
Count: 44.

---

## 3. Dispatch Architecture

The wall-knob dispatch is in:
- **Source of truth (Python):** `tools/ai_design/wall_knob_calibration.py` — 44-entry `CALIBRATION` dict (was 40; 4 new state civs added: ANWCalifornians, ANWCentralAmericans, ANWBajaCalifornians, ANWRioGrande)
- **Generated XS:** `game/ai/core/aiWallKnobsByCiv.xs` — emitted by `calibration.py --emit-xs`; currently still **40-civ** (4 new entries are in the .py but the .xs has not been re-emitted)
- **Called from:** `aiLoaderStandard.xs::preInit()` after `initLeader<Name>()`
- **Build-style & fallback strategy:** some civs also set `gANWWallStrategy` directly in `game/ai/leaders/leaderCommon.xs` lines 1214–1408

The dispatch XS matches `kbGetCivName(cMyCiv)`. For ANW canonical nation civs (ANWBritish, ANWChinese, etc.), `kbGetCivName` returns "ANWBritish" etc. (confirmed at leaderCommon.xs line 1212). Because the dispatch XS only has entries for base engine tokens ("British", "Chinese", etc.) and the revolution ANW tokens, all 22 ANW canonical nation tokens **fall through to the `else` default block** (`game/ai/core/aiWallKnobsByCiv.xs` final else branch) and get factory defaults from aiHeader.xs.

**The dispatch XS currently handles 43 civ keys** (grep of `civKey ==` in aiWallKnobsByCiv.xs). The 4 new state civs are in the .py but the .xs was not yet re-emitted.

---

## 4. Have / Missing Analysis

### 4a. Fully covered — strategy EXPLICITLY set

These appear by name in `aiWallKnobsByCiv.xs` (generated from calibration.py) OR have `gANWWallStrategy` explicitly set in `leaderCommon.xs`.

| ANW Token | Dispatch Source | Strategy |
|-----------|----------------|----------|
| ANWNapoleonicFrance | aiWallKnobsByCiv.xs | 5 Mobile |
| ANWRevFrance | aiWallKnobsByCiv.xs | 4 Urban |
| ANWCanadians | aiWallKnobsByCiv.xs | 0 Fortress |
| ANWBrazil | aiWallKnobsByCiv.xs | 3 Frontier |
| ANWArgentines | aiWallKnobsByCiv.xs | 5 Mobile |
| ANWChileans | aiWallKnobsByCiv.xs | 0 Fortress |
| ANWPeruvians | aiWallKnobsByCiv.xs | 0 Fortress |
| ANWColumbians | aiWallKnobsByCiv.xs | 5 Mobile |
| ANWHaitians | aiWallKnobsByCiv.xs | 1 Chokepoint |
| ANWIndonesians | aiWallKnobsByCiv.xs | 1 Chokepoint |
| ANWSouthAfricans | aiWallKnobsByCiv.xs | 2 Coastal |
| ANWFinnish | aiWallKnobsByCiv.xs | 0 Fortress |
| ANWHungarians | aiWallKnobsByCiv.xs | 5 Mobile |
| ANWRomanians | aiWallKnobsByCiv.xs | 3 Frontier |
| ANWBarbary | aiWallKnobsByCiv.xs | 2 Coastal |
| ANWEgyptians | aiWallKnobsByCiv.xs | 0 Fortress |
| ANWMayans | aiWallKnobsByCiv.xs | 1 Chokepoint |
| ANWTexians | aiWallKnobsByCiv.xs | 5 Mobile |
| ANWCalifornians | calibration.py (XS not yet re-emitted) | 5 Mobile |
| ANWCentralAmericans | calibration.py (XS not yet re-emitted) | 3 Frontier |
| ANWBajaCalifornians | calibration.py (XS not yet re-emitted) | 2 Coastal |
| ANWRioGrande | calibration.py (XS not yet re-emitted) | 3 Frontier |
| ANWAztecs | leaderCommon.xs line 1218 | 1 Chokepoint |
| ANWFrench | leaderCommon.xs line 1266 | 0 Fortress |
| ANWInca | leaderCommon.xs line 1302 | 0 Fortress |
| ANWRussians | leaderCommon.xs line 1377 | 3 Frontier |

**26 civs covered.** 

### 4b. Missing — fall through to default (strategy=0 by accident)

These 18 ANW canonical nation tokens have no entry in `aiWallKnobsByCiv.xs` and do NOT set `gANWWallStrategy` in `leaderCommon.xs`. They inherit the aiHeader.xs default of `0` (FortressRing), which may or may not be intentional.

Source evidence: leaderCommon.xs lines 1224–1408 — none of these branches assign `gANWWallStrategy`.

| ANW Token | `kbGetCivName` key | leaderCommon.xs style call | Default (accidental) |
|-----------|---------------------|----------------------------|----------------------|
| ANWBritish | "ANWBritish" | `anwUseNavalMercantileCompoundStyle(2)` | 0 (wrong — should be 2 Coastal) |
| ANWChinese | "ANWChinese" | `anwUseCompactFortifiedCoreStyle(4, true)` | 0 (acceptable — matches Fortress) |
| ANWDutch | "ANWDutch" | `anwUseNavalMercantileCompoundStyle(2)` | 0 (wrong — should be 2 Coastal) |
| ANWEthiopians | "ANWEthiopians" | `anwUseHighlandCitadelStyle(3)` | 0 (acceptable — Fortress matches Highland) |
| ANWGermans | "ANWGermans" | `anwUseRepublicanLeveeStyle(2, true)` | 0 (wrong — base Germans = 4 Urban) |
| ANWHaudenosaunee | "ANWHaudenosaunee" | `anwUseShrineTradeNodeSpreadStyle(1)` | 0 (wrong — should be 5 Mobile, mirrors XPIroquois) |
| ANWHausa | "ANWHausa" | `anwUseDistributedEconomicNetworkStyle(2)` | 0 (wrong — base DEHausa = 3 Frontier) |
| ANWIndians | "ANWIndians" | `anwUseHighlandCitadelStyle(5)` | 0 (acceptable — Fortress matches Highland) |
| ANWItalians | "ANWItalians" | `anwUseRepublicanLeveeStyle(2, true)` | 0 (wrong — base DEItalians = 4 Urban) |
| ANWJapanese | "ANWJapanese" | `anwUseShrineTradeNodeSpreadStyle(3)` | 0 (wrong — base Japanese = 5 Mobile) |
| ANWLakota | "ANWLakota" | `anwUseSteppeCavalryWedgeStyle(0)` | 0 (wrong — should be 5 Mobile, mirrors XPSioux) |
| ANWMaltese | "ANWMaltese" | `anwUseHighlandCitadelStyle(5)` | 0 (acceptable — DEMaltese = 0 Fortress) |
| ANWMexicans | "ANWMexicans" | `anwUseRepublicanLeveeStyle(0)` | 0 (wrong — base DEMexicans = 4 Urban) |
| ANWOttomans | "ANWOttomans" | `anwUseSiegeTrainConcentrationStyle(3)` | 0 (acceptable — Ottomans = 0 Fortress) |
| ANWPortuguese | "ANWPortuguese" | `anwUseNavalMercantileCompoundStyle(2)` | 0 (wrong — should be 2 Coastal) |
| ANWSpanish | "ANWSpanish" | `anwUseForwardOperationalLineStyle(2)` | 0 (wrong — base Spanish = 5 Mobile) |
| ANWSwedes | "ANWSwedes" | `anwUseForwardOperationalLineStyle(1)` | 0 (wrong — base DESwedish = 5 Mobile) |
| ANWUSA | "ANWUSA" | `anwUseRepublicanLeveeStyle(1)` | 0 (wrong — base DEAmericans = 4 Urban) |

**18 civs with missing/wrong wall strategy dispatch.**

> **Reconciling against "26 missing" in prior audit:** the prior audit likely counted from the set of 44 canonical ANW tokens vs. entries in `aiWallKnobsByCiv.xs`. The dispatch XS has 43 `civKey ==` branches, but 22 of those are for the revolution civs (ANW* keys directly). The remaining 21 base-token branches ("British", "Chinese", etc.) cover base engine tokens, NOT the ANWBritish etc. picker tokens. So from the XS perspective, 22 ANW canonical nation tokens are missing — minus the 4 that were already handled via leaderCommon.xs explicit sets = 18 truly unhandled. The discrepancy (26 vs 18) may reflect the 4 new state-civ entries (Californians etc.) not yet re-emitted to XS at the time of the prior audit — those 4 would have also been "missing" then (26 = 22 + 4).

---

## 5. Proposed Strategy per Missing Civ

The base-civ calibration entries provide the authoritative mapping. The principle is: ANW canonical nation version mirrors its base-engine counterpart's strategy.

| ANW Token | Base Engine Token | Base Strategy | Proposed Strategy | Rationale |
|-----------|------------------|---------------|-------------------|-----------|
| ANWBritish | British | 2 Coastal | **2 Coastal** | Naval doctrine, island/coastal terrain (leaderCommon sets NavalMercantile style) |
| ANWChinese | Chinese | 0 Fortress | **0 Fortress** | Default already correct; Great Wall doctrine |
| ANWDutch | Dutch | 2 Coastal | **2 Coastal** | Dyke/coastal defense, NavalMercantile style |
| ANWEthiopians | DEEthiopians | 0 Fortress | **0 Fortress** | Default already correct; Highland citadel |
| ANWGermans | Germans | 4 Urban | **4 Urban** | Prussian barricade/drill-yard; leaderCommon sets RepublicanLevee |
| ANWHaudenosaunee | XPIroquois | 5 Mobile | **5 Mobile** | Longhouse confederation, no perimeter; mirrors XPIroquois exactly |
| ANWHausa | DEHausa | 3 Frontier | **3 Frontier** | Caravanserai frontier palisade; DistributedEconomicNetwork style |
| ANWIndians | Indians | 0 Fortress | **0 Fortress** | Default already correct; hill-fort citadel |
| ANWItalians | DEItalians | 4 Urban | **4 Urban** | Risorgimento urban barricade; RepublicanLevee style |
| ANWJapanese | Japanese | 5 Mobile | **5 Mobile** | Tokugawa samurai field army; ShrineTradeNodeSpread style |
| ANWLakota | XPSioux | 5 Mobile | **5 Mobile** | Plains horse warriors; SteppeCavalryWedge style |
| ANWMaltese | DEMaltese | 0 Fortress | **0 Fortress** | Default already correct; Hospitaller siege fortress |
| ANWMexicans | DEMexicans | 4 Urban | **4 Urban** | Hidalgo insurgente town barricade; RepublicanLevee style |
| ANWOttomans | Ottomans | 0 Fortress | **0 Fortress** | Default already correct; Janissary double ring |
| ANWPortuguese | Portuguese | 2 Coastal | **2 Coastal** | Carrack Atlantic empire; NavalMercantile style |
| ANWSpanish | Spanish | 5 Mobile | **5 Mobile** | Reconquista mobile column; ForwardOperationalLine style |
| ANWSwedes | DESwedish | 5 Mobile | **5 Mobile** | Caroline mobile doctrine; ForwardOperationalLine style |
| ANWUSA | DEAmericans | 4 Urban | **4 Urban** | Continental Army barricade; RepublicanLevee style |

**Summary of proposed strategies for 18 missing:**
- 5 civs already have the correct default (0 Fortress): ANWChinese, ANWEthiopians, ANWIndians, ANWMaltese, ANWOttomans
- 4 need Coastal (2): ANWBritish, ANWDutch, ANWPortuguese *(and ANWBarbary already covered)*
- 3 need Urban (4): ANWGermans, ANWItalians, ANWMexicans, ANWUSA *(4 actually)*
- 4 need Mobile (5): ANWHaudenosaunee, ANWJapanese, ANWLakota, ANWSpanish, ANWSwedes *(5 actually)*
- 1 needs Frontier (3): ANWHausa

Corrected count: 5 default-OK + 3 Coastal + 4 Urban + 5 Mobile + 1 Frontier = 18. ✓

---

## 6. Fix: What to Add to `wall_knob_calibration.py`

The fix is to add 18 entries to `CALIBRATION` in `tools/ai_design/wall_knob_calibration.py`, then re-emit the XS with:

```
python3 tools/ai_design/wall_knob_calibration.py --emit-xs > game/ai/core/aiWallKnobsByCiv.xs
```

**JSON shape (per-civ entry in the Python dict):**

```python
"ANWBritish": dict(
    rev_token="ANWBritish", strategy=2,
    radius=22, gates=4, age2stone=1, trigger_age=2, seg_len=20,
    towers=6, secondary=0, vils=6, fwd_bias=0.20, outer_ring=4,
    outposts=2, repair=3, closure_pct=100, no_water=1,
    doctrine="Channel-defense coastal — mirrors British (Elizabeth) exactly"),
```

Key fields that **must** match the base-civ counterpart:
- `strategy`: see proposed table above
- `rev_token`: set to the ANW token string (e.g. `"ANWBritish"`)
- All knob values: copy from the base-civ entry (e.g. copy `British` dict for `ANWBritish`)

**The 4 new state civs (ANWCalifornians, ANWCentralAmericans, ANWBajaCalifornians, ANWRioGrande)** are already in `calibration.py` but the XS has not been re-emitted. These need a re-emit only — no new calibration rows required.

---

## 7. File References

| File | Purpose | Key Lines |
|------|---------|-----------|
| `game/ai/aiHeader.xs` | Enum definition | 202–207, 209 |
| `game/ai/core/aiWallKnobsByCiv.xs` | Generated dispatch XS | full file (43 `civKey ==` branches) |
| `tools/ai_design/wall_knob_calibration.py` | Python source of truth | 42–380 (CALIBRATION dict) |
| `game/ai/leaders/leaderCommon.xs` | Explicit strategy overrides | 1214–1408 |
| `data/civmods.xml` | Canonical 44-civ list | `<name>` + `<main>1</main>` pairs |
| `artifacts/validation/per_civ_wall_knobs.json` | Validation run results | top-level: 40 civs all PASS |
| `tools/validation/validate_per_civ_wall_knobs.py` | Validator | CALIB_TO_SPEC map line 122–163 |

---

## 8. Action Summary for Implementation Pass

1. **Re-emit XS now** (4 new state civs in calibration.py already, XS stale):  
   `python3 tools/ai_design/wall_knob_calibration.py --emit-xs > game/ai/core/aiWallKnobsByCiv.xs`

2. **Add 18 ANW canonical nation entries** to `CALIBRATION` in `wall_knob_calibration.py`, using the table in §5 and the JSON shape in §6. Copy knob values from the corresponding base-civ entry; only the `rev_token` key differs.

3. **Re-emit XS again** after adding the 18 entries.

4. **Re-run validator**: `python3 -m tools.validation.validate_per_civ_wall_knobs` — should now report 62 civs PASS (44 + 18 = 62 total in calibration after the adds).

5. **Update `CALIB_TO_SPEC`** in `validate_per_civ_wall_knobs.py` (line 122) to map the 18 new engine tokens to their spec keys.

> **No change to `leaderCommon.xs`** needed for the 4 civs whose default is already correct (ANWChinese, ANWEthiopians, ANWIndians, ANWMaltese, ANWOttomans). However adding them to calibration.py is still recommended for consistency — the dispatch's `else` fallback + explicit leaderCommon.xs `gANWWallStrategy` set should be replaced by a single dispatch entry.
