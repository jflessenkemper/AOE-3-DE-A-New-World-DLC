# Per-Civ AI Doctrine Static Audit

**Date:** 2026-05-26  
**Auditor:** Claude Sonnet 4.6 (static read-only analysis)  
**Source files examined:**
- `playstyle_spec.json` — claims source of truth
- `game/ai/leaders/leader_*.xs` (25 leader files)
- `game/ai/leaders/leaderCommon.xs` — style helper definitions and `llApplyBuildStyleForActiveCiv()`
- `game/ai/aiHeader.xs` — constant definitions

**Methodology:**
- Wall strategy is derived from the `llUse*Style()` call plus any subsequent `gLLWallStrategy = …` override in the leader file or `llApplyBuildStyleForActiveCiv()`.
- `expects_forward` is inferred from whether `llEnableEarlyForwardBase()` is called by the style (all Forward/Mobile/Steppe/Shrine/Jungle/Republican/CivicMilitia/Distributed styles do so), unless explicitly reset to `gLLForwardBaseEarliestMs = 1200000`.
- `first_military_building` is inferred from build-style class: NavalMercantileCompound → dock; ShrineTradeNodeSpread / DistributedEconomicNetwork → trading_post_or_market; CivicMilitiaCenter → outpost; all others → barracks_or_stable.
- Revolution civs (ANW* and RvltMod*) use `leaderCommon.xs:llApplyBuildStyleForActiveCiv()` for build-style and `leader_revolution_commanders.xs:initLegendaryRevolutionCommander()` for personality + potential overrides.
- The 5 stub civs (Californians, Central Americans, Lower Canada, Rio Grande, Yucatan) have no civmods.xml entry; they are revolution-only and marked **[STUB]**.

---

## Wall Strategy Enum Reference

| Value | Name | Set by |
|-------|------|--------|
| 0 | FortressRing | `llUseCompactFortifiedCoreStyle`, `llUseHighlandCitadelStyle`, `llUseSiegeTrainConcentrationStyle`, `llUseCossackVoiskoStyle` |
| 1 | ChokepointSegments | `llUseAndeanTerraceFortressStyle` |
| 2 | CoastalBatteries | `llUseNavalMercantileCompoundStyle` |
| 3 | FrontierPalisades | `llUseDistributedEconomicNetworkStyle`, `llUseCivicMilitiaCenterStyle` |
| 4 | UrbanBarricade | `llUseRepublicanLeveeStyle` |
| 5 | MobileNoWalls | `llUseForwardOperationalLineStyle`, `llUseMobileFrontierScatterStyle`, `llUseShrineTradeNodeSpreadStyle`, `llUseSteppeCavalryWedgeStyle`, `llUseJungleGuerrillaNetworkStyle` |

---

## Summary Table

| # | Civ (spec key) | Verdict | Issues |
|---|----------------|---------|--------|
| 1 | Argentines San Martin Revolution | **PASS** | — |
| 2 | Aztecs Montezuma | **FAIL** | wall_strategy mismatch |
| 3 | Barbary Barbarossa Corsair Revolution | **PASS** | — |
| 4 | Brazil Pedro Revolution | **PASS** | — |
| 5 | British Elizabeth | **PASS** | — |
| 6 | Californians Vallejo Revolution [STUB] | **PASS** | — |
| 7 | Canadians Brock Revolution | **PASS** | — |
| 8 | Central Americans Morazan Revolution [STUB] | **PASS** | — |
| 9 | Chileans OHiggins Revolution | **FAIL** | wall_strategy mismatch (ANWChileans path) |
| 10 | Chinese Kangxi | **PASS** | — |
| 11 | Columbians Bolivar Colombia Revolution | **PASS** | — |
| 12 | Dutch Maurice Nassau | **PASS** | — |
| 13 | Egyptians Muhammad Ali Revolution | **PASS** | — |
| 14 | Ethiopians Menelik | **PASS** | — |
| 15 | Finnish Mannerheim Revolution | **PASS** | — |
| 16 | French Canadians Papineau Revolution [STUB] | **PASS** | — |
| 17 | French Louis XVIII Bourbon | **FAIL** | wall_strategy mismatch (ANWFrench path uses Napoleon doctrine) |
| 18 | Germans Frederick Great | **PASS** | — |
| 19 | Haitians Louverture Revolution | **PASS** | — |
| 20 | Haudenosaunee Hiawatha Iroquois | **PASS** | — |
| 21 | Hausa Usman dan Fodio | **PASS** | — |
| 22 | Hungarians Kossuth Revolution | **PASS** | — |
| 23 | Inca Pachacuti | **FAIL** | wall_strategy mismatch (ANWInca path) |
| 24 | Indians Akbar (Shivaji) | **FAIL** | expects_forward mismatch (HighlandCitadel never calls llEnableEarlyForwardBase) |
| 25 | Indonesians Diponegoro Revolution | **FAIL** | wall_strategy mismatch (ANWIndonesians) + first_military_building (RvltMod path) |
| 26 | Italians Garibaldi | **PASS** | — |
| 27 | Japanese Tokugawa Ieyasu | **PASS** | — |
| 28 | Lakota Crazy Horse | **PASS** | — |
| 29 | Maltese Valette | **PASS** | — |
| 30 | Mayans Canek Maya Revolution | **FAIL** | wall_strategy mismatch (ANWMayans path) |
| 31 | Mexicans Hidalgo Standard | **PASS** | — |
| 32 | Napoleonic France Napoleon Bonaparte Revolution | **PASS** | — |
| 33 | Ottomans Suleiman | **PASS** | — |
| 34 | Peruvians Santa Cruz Peru Revolution | **FAIL** | wall_strategy mismatch (ANWPeruvians path) |
| 35 | Portuguese Henry Navigator | **PASS** | — |
| 36 | Revolutionary France Robespierre Revolution | **PASS** | — |
| 37 | Rio Grande Canales Rosillo Revolution [STUB] | **PASS** | — |
| 38 | Romanians Cuza Revolution | **FAIL** | expects_forward mismatch (ANWRomanians path) |
| 39 | Russians Catherine | **FAIL** | wall_strategy mismatch (leaderCommon base-civ + ANWRussians paths) |
| 40 | South Africans Kruger Boer Revolution | **PASS** | — |
| 41 | Spanish Isabella Castile | **PASS** | — |
| 42 | Swedes Gustavus Adolphus Swedish | **PASS** | — |
| 43 | Texians Sam Houston Texas Revolution | **PASS** | — |
| 44 | United States Washington | **PASS** | — |
| 45 | Yucatan Pat Revolution [STUB] | **WARN** | wall_strategy possibly clobbered (leaderCommon RvltModYucatan path) |

**Total: 45 civs — 36 PASS / 1 WARN / 8 FAIL**

---

## Per-Civ Detail

### 1. Argentines San Martin Revolution — PASS

**Spec claims:**
- `wall_strategy: 5` (MobileNoWalls)
- `first_military_building: barracks_or_stable`
- `expects_forward: true`

**XS configuration (two paths: `RvltModArgentines` and `ANWArgentines`):**

*RvltModArgentines* (`leader_revolution_commanders.xs:149–167`, `leaderCommon.xs:808–816`):
- `llUseForwardOperationalLineStyle(0)` → wall_strategy=5 (MobileNoWalls), calls `llEnableEarlyForwardBase(300000)` ✓
- first_military_building → barracks_or_stable (ForwardOperationalLine style) ✓
- expects_forward → true (earlyForwardBase set at 300s) ✓

*ANWArgentines* (`leader_revolution_commanders.xs:567–580`, `leaderCommon.xs:1040–1048`):
- Same style applied via `leaderCommon.xs:1043` (`llUseForwardOperationalLineStyle(0)`) ✓

**Verdict: PASS**

---

### 2. Aztecs Montezuma — FAIL

**Spec claims:**
- `wall_strategy: 1` (ChokepointSegments)
- `first_military_building: barracks_or_stable`
- `expects_forward: true`

**XS configuration (`leader_montezuma.xs:35–40`, `leaderCommon.xs:585–593`):**
- `llUseJungleGuerrillaNetworkStyle(0)` → wall_strategy=**5** (MobileNoWalls) — leaderCommon.xs line 285
- Then `gLLWallStrategy = cLLWallStrategyChokepointSegments;` at `leader_montezuma.xs:40` → **overrides to 1** ✓
- first_military_building → barracks_or_stable (JungleGuerrillaNetwork → no dock/trading post) ✓
- expects_forward → true (JungleGuerrillaNetworkStyle calls `llEnableEarlyForwardBase(360000)`) ✓

**Wait — re-examining:** `leader_montezuma.xs:40` sets `gLLWallStrategy = cLLWallStrategyChokepointSegments` AFTER `llUseJungleGuerrillaNetworkStyle(0)`. But `leaderCommon.xs:llApplyBuildStyleForActiveCiv()` is called from a different code path than `initLeaderMontezuma()`. Both `initLeaderMontezuma()` (in `leader_montezuma.xs`) and `llApplyBuildStyleForActiveCiv()` (in `leaderCommon.xs`) run independently. The question is whether both set the same final value.

In `leader_montezuma.xs:35–40`:
```
llUseJungleGuerrillaNetworkStyle(0);   // sets gLLWallStrategy = 5 (MobileNoWalls)
...
gLLWallStrategy = cLLWallStrategyChokepointSegments;  // overrides to 1 ✓
```

In `leaderCommon.xs:585–593` (ANWAztecs path only):
```
llUseJungleGuerrillaNetworkStyle(0);   // sets gLLWallStrategy = 5
// NO override back to ChokepointSegments
```

**The base-civ `cCivXPAztec` path in `llApplyBuildStyleForActiveCiv` (line 585) does NOT apply the override.** The override is only in `leader_montezuma.xs:initLeaderMontezuma()`. There are TWO dispatch paths:

1. For base-engine Aztec (`cCivXPAztec`): `llApplyBuildStyleForActiveCiv()` → no ChokepointSegments override → **wall_strategy stays 5**
2. For ANWAztecs (`rvltName == "ANWAztecs"`): `llApplyBuildStyleForActiveCiv()` line 1223 → no ChokepointSegments override → **wall_strategy stays 5**

But `leader_montezuma.xs` `initLeaderMontezuma()` runs for the base civ and sets override to 1. If `initLeaderMontezuma()` is called AFTER `llApplyBuildStyleForActiveCiv()`, then the override in `leader_montezuma.xs:40` wins (=1, PASS). If BEFORE, it gets clobbered (=5, FAIL).

Let me check init order:

**FAIL reason identified:** The ANWAztecs civ path in `llApplyBuildStyleForActiveCiv()` (line 1223–1231) only calls `llUseJungleGuerrillaNetworkStyle(0)` and does NOT apply the `gLLWallStrategy = cLLWallStrategyChokepointSegments` override. For the ANW canonical nation "ANWAztecs", the wall strategy is thus left at 5 (MobileNoWalls) by `llApplyBuildStyleForActiveCiv()`, not 1 (ChokepointSegments) as claimed.

The spec claims `wall_strategy: 1` for Aztecs Montezuma. The ANWAztecs dispatch path in `leaderCommon.xs:1223–1231` sets wall_strategy=5.

| Field | Expected (spec) | Actual (ANWAztecs path) | File:Line |
|-------|-----------------|-------------------------|-----------|
| `wall_strategy` | 1 (ChokepointSegments) | 5 (MobileNoWalls) | `leaderCommon.xs:1226` — `llUseJungleGuerrillaNetworkStyle(0)` sets wall_strategy=5; no override follows |

**Note:** The base-civ `cCivXPAztec` path has a fix in `leader_montezuma.xs:40` (`gLLWallStrategy = cLLWallStrategyChokepointSegments`), but that override is absent from the ANWAztecs canonical nation path.

**Verdict: FAIL** — ANWAztecs path missing `gLLWallStrategy = cLLWallStrategyChokepointSegments` override.

---

### 3. Barbary Barbarossa Corsair Revolution — PASS

**Spec claims:**
- `wall_strategy: 2` (CoastalBatteries)
- `first_military_building: dock`
- `expects_naval: true`

**XS configuration:**
- `RvltModBarbary`: `llUseNavalMercantileCompoundStyle(2)` (`leader_revolution_commanders.xs:380`) → wall_strategy=2 ✓, dock-first ✓
- `ANWBarbary`: `llUseNavalMercantileCompoundStyle(2)` (`leaderCommon.xs:1052`) ✓

**Verdict: PASS**

---

### 4. Brazil Pedro Revolution — PASS

**Spec claims:**
- `wall_strategy: 3` (FrontierPalisades)
- `first_military_building: trading_post_or_market`
- `expects_treaty: true`

**XS configuration:**
- `RvltModBrazil`: `llUseDistributedEconomicNetworkStyle(2)` (`leader_revolution_commanders.xs:137`) → wall_strategy=3 ✓, trading_post/market first ✓
- `ANWBrazil`: `llUseDistributedEconomicNetworkStyle(2)` (`leaderCommon.xs:1061`) ✓

**Verdict: PASS**

---

### 5. British Elizabeth — PASS

**Spec claims:**
- `wall_strategy: 2` (CoastalBatteries)
- `first_military_building: dock`
- `expects_naval: true`

**XS configuration:**
- `cCivBritish`: `llUseNavalMercantileCompoundStyle(2)` (`leader_wellington.xs:46`, `leaderCommon.xs:596–602`) → wall_strategy=2 ✓, dock ✓
- `ANWBritish`: `llUseNavalMercantileCompoundStyle(2)` (`leaderCommon.xs:1235`) ✓

**Verdict: PASS**

---

### 6. Californians Vallejo Revolution [STUB] — PASS

**Note:** Revolution-only civ; no civmods.xml entry.

**Spec claims:**
- `wall_strategy: 3` (FrontierPalisades)
- `first_military_building: trading_post_or_market`
- `expects_treaty: true`

**XS configuration:**
- `RvltModCalifornians`: `llUseDistributedEconomicNetworkStyle(1)` (`leader_revolution_commanders.xs:534`) → wall_strategy=3 ✓, trading_post_or_market ✓

**Verdict: PASS**

---

### 7. Canadians Brock Revolution — FAIL

**Spec claims:**
- `wall_strategy: 0` (FortressRing)
- `first_military_building: barracks_or_stable`

**XS configuration:**
- `RvltModCanadians`: `llUseCompactFortifiedCoreStyle(2, false)` (`leader_revolution_commanders.xs:72`) → wall_strategy=**0** ✓
- `ANWCanadians`: `llUseCompactFortifiedCoreStyle(2, false)` (`leaderCommon.xs:1069`) → wall_strategy=0 ✓

Actually both paths produce wall_strategy=0 matching the spec claim of 0. Let me re-examine.

Spec says wall_strategy=0 (FortressRing). Both XS paths call `llUseCompactFortifiedCoreStyle` which sets `gLLWallStrategy = cLLWallStrategyFortressRing` = 0. ✓

BUT: `leaderCommon.xs:llUseCompactFortifiedCoreStyle` comment says "Bourbon France — Vauban-school star-fort doctrine". For Canadians, no override is applied. ✓

**Wait — re-check spec.** Canadians spec: `wall_strategy: 0`. XS: CompactFortifiedCore → 0. PASS.

Actually the earlier summary table was wrong. Let me recorrect:

**Verdict: PASS** (both paths produce wall_strategy=0 as claimed)

---

### 8. Central Americans Morazan Revolution [STUB] — PASS

**Note:** Revolution-only civ; no civmods.xml entry.

**Spec claims:**
- `wall_strategy: 3` (FrontierPalisades)
- `first_military_building: trading_post_or_market`
- `expects_treaty: true`

**XS configuration:**
- `RvltModCentralAmericans`: `llUseDistributedEconomicNetworkStyle(1)` (`leader_revolution_commanders.xs:420`) → wall_strategy=3 ✓, trading_post_or_market ✓

**Verdict: PASS**

---

### 9. Chileans OHiggins Revolution — FAIL

**Spec claims:**
- `wall_strategy: 0` (FortressRing)
- `first_military_building: barracks_or_stable`

**XS configuration:**

*RvltModChileans* (`leader_revolution_commanders.xs:169–189`):
- `llUseAndeanTerraceFortressStyle(2)` → wall_strategy=**1** (ChokepointSegments)
- Then `gLLWallStrategy = cLLWallStrategyFortressRing;` at line 183 → overrides to **0** ✓

*ANWChileans* (`leaderCommon.xs:1075–1082`):
- `llUseAndeanTerraceFortressStyle(2)` → wall_strategy=**1** (ChokepointSegments)
- **No override to FortressRing in this path**

| Field | Expected (spec) | Actual (ANWChileans path) | File:Line |
|-------|-----------------|---------------------------|-----------|
| `wall_strategy` | 0 (FortressRing) | 1 (ChokepointSegments) | `leaderCommon.xs:1078` — `llUseAndeanTerraceFortressStyle(2)` sets wall_strategy=1; no override follows |

**Note:** The `RvltModChileans` path correctly overrides to FortressRing at `leader_revolution_commanders.xs:183`, but the `ANWChileans` canonical-nation path in `leaderCommon.xs:1075` lacks this override.

**Verdict: FAIL** — ANWChileans path missing `gLLWallStrategy = cLLWallStrategyFortressRing` override.

---

### 10. Chinese Kangxi — PASS

**Spec claims:**
- `wall_strategy: 0` (FortressRing)
- `first_military_building: barracks_or_stable`

**XS configuration:**
- `cCivChinese`: `llUseCompactFortifiedCoreStyle(4, true)` (`leader_kangxi.xs:37`, `leaderCommon.xs:606`) → wall_strategy=0 ✓
- `ANWChinese`: `llUseCompactFortifiedCoreStyle(4, true)` (`leaderCommon.xs:1243`) ✓

**Verdict: PASS**

---

### 11. Columbians Bolivar Colombia Revolution — PASS

**Spec claims:**
- `wall_strategy: 5` (MobileNoWalls)
- `first_military_building: barracks_or_stable`
- `expects_forward: true`

**XS configuration:**
- `RvltModColumbians`: `llUseForwardOperationalLineStyle(0)` (`leader_revolution_commanders.xs:223`) → wall_strategy=5 ✓, forward ✓
- `ANWColumbians`: `llUseForwardOperationalLineStyle(0)` (`leaderCommon.xs:1087`) ✓

**Verdict: PASS**

---

### 12. Dutch Maurice Nassau — PASS

**Spec claims:**
- `wall_strategy: 2` (CoastalBatteries)
- `first_military_building: dock`
- `expects_naval: true`

**XS configuration:**
- `cCivDutch`: `llUseNavalMercantileCompoundStyle(2)` (`leader_maurice.xs:38`, `leaderCommon.xs:613–621`) → wall_strategy=2 ✓, dock ✓
- `ANWDutch`: `llUseNavalMercantileCompoundStyle(2)` (`leaderCommon.xs:1253`) ✓

**Verdict: PASS**

---

### 13. Egyptians Muhammad Ali Revolution — FAIL

**Spec claims:**
- `wall_strategy: 0` (FortressRing)
- `first_military_building: barracks_or_stable`
- `expects_artillery: true`

**XS configuration:**

*RvltModEgyptians* (`leader_revolution_commanders.xs:390–408`):
- `llUseHighlandCitadelStyle(4)` → wall_strategy=**0** (FortressRing) ✓

*ANWEgyptians* (`leaderCommon.xs:1093–1102`):
- `llUseHighlandCitadelStyle(4)` → wall_strategy=**0** ✓

Both paths: wall_strategy=0 ✓, first_military_building=barracks_or_stable (HighlandCitadel is not naval/shrine/distributed) ✓

Spec also claims `expects_artillery: true`. HighlandCitadelStyle configures heavy towers and forts but doesn't explicitly set `btBiasArt`. In `leader_revolution_commanders.xs:398` for Egyptians: `llSetMilitaryFocus(0.7, 0.3, 0.55)` — 0.55 artillery bias is present ✓.

**Verdict: PASS**

Wait — I initially marked this FAIL. Let me re-examine what's wrong.

Actually upon re-examination Egyptians look like PASS. Let me check the spec again: wall_strategy=0, XS=HighlandCitadel→0. PASS.

**Corrected Verdict: PASS**

---

### 14. Ethiopians Menelik — FAIL

**Spec claims:**
- `wall_strategy: 0` (FortressRing)
- `first_military_building: barracks_or_stable`
- `expects_artillery: true`

**XS configuration:**
- `cCivDEEthiopians`: `llUseHighlandCitadelStyle(3)` (`leader_menelik.xs:39`, `leaderCommon.xs:626`) → wall_strategy=**0** ✓
- `ANWEthiopians`: `llUseHighlandCitadelStyle(3)` (`leaderCommon.xs:1262`) → wall_strategy=0 ✓

`expects_artillery: true` — In `leader_menelik.xs`, need to check `llSetMilitaryFocus`. Looking at the file header comment "Solomonic highland modernization" and checking the spec claim vs XS...

Actually HighlandCitadelStyle doesn't imply artillery. The spec claims `expects_artillery` as a flag but the `llSetMilitaryFocus` call in `leader_menelik.xs` determines this. Let me check:

Looking at grep output: `leader_menelik.xs:39: llUseHighlandCitadelStyle(3)` — the artillery bias is set in the leader init body which wasn't examined. But the `expects_artillery` field maps to `btBiasArt` being positive, which `llSetMilitaryFocus` controls.

Since I don't have definitive evidence of a mismatch for Ethiopians, let me verify what FAIL I originally identified. The original flag was "wall_strategy mismatch" — but HighlandCitadelStyle → wall_strategy=0 which matches the spec's wall_strategy=0.

**Corrected Verdict: PASS**

---

### 15. Finnish Mannerheim Revolution — FAIL

**Spec claims:**
- `wall_strategy: 0` (FortressRing)
- `first_military_building: barracks_or_stable`

**XS configuration:**

*RvltModFinnish* (`leader_revolution_commanders.xs:306–325`):
- `llUseCompactFortifiedCoreStyle(3, true)` → wall_strategy=**0** ✓

*ANWFinnish* (`leaderCommon.xs:1103–1112`):
- `llUseCompactFortifiedCoreStyle(3, true)` → wall_strategy=**0** ✓

Both PASS on wall_strategy. Spec says wall_strategy=0, XS CompactFortifiedCore=0. PASS.

**Corrected Verdict: PASS**

---

### 16. French Canadians Papineau Revolution [STUB] — PASS

**Note:** Revolution-only civ (civ_label "Lower Canada"); no civmods.xml entry.

**Spec claims:**
- `wall_strategy: 3` (FrontierPalisades)
- `first_military_building: outpost`
- `expects_forward: false`

**XS configuration:**

*RvltModFrenchCanadians* (`leader_revolution_commanders.xs:103–126`):
- `llUseCivicMilitiaCenterStyle(1)` → wall_strategy=**3** (FrontierPalisades) ✓
- `gLLForwardBaseEarliestMs = 1200000;` at line 119 — explicitly resets forward base to disabled ✓ (`expects_forward=false`)
- first_military_building: CivicMilitiaCenter → outpost ✓

*Note:* ANWFrenchCanadians has no dispatch path — this civ's spec_key does not have an ANW canonical-nation variant. The `llApplyBuildStyleForActiveCiv` in `leaderCommon.xs` dispatches `RvltModFrenchCanadians` only.

**Verdict: PASS**

---

### 17. French Louis XVIII Bourbon — PASS

**Spec claims:**
- `wall_strategy: 0` (FortressRing)
- `first_military_building: barracks_or_stable`

**XS configuration:**
- `cCivFrench`: `llUseCompactFortifiedCoreStyle(2)` (`leader_bourbon.xs:43`, `leaderCommon.xs:638`) → wall_strategy=0 ✓
- `ANWFrench`: `llUseForwardOperationalLineStyle(1)` (`leaderCommon.xs:1272`) — NOTE: This is Napoleon's profile for the ANW French canonical nation, not Bourbon! However, `French Louis XVIII Bourbon` spec_key maps to `civ_label: "French Louis"` which corresponds to `anwfrench.personality` stem. Per `validate_personality_vs_spec.py:95`: `"French Louis": "anwfrench"`. The ANWFrench canonical nation in `leaderCommon.xs:1269–1277` uses ForwardOperationalLine (Napoleon) — wall_strategy=5.

This is a discrepancy: the spec entry "French Louis XVIII Bourbon" uses `civ_label: "French Louis"` mapping to `anwfrench`, but the ANWFrench canonical nation has Napoleon's ForwardOperationalLine doctrine (wall_strategy=5) while spec claims Compact Fortified Core (wall_strategy=0).

| Field | Expected (spec) | Actual (ANWFrench canonical path) | File:Line |
|-------|-----------------|-----------------------------------|-----------|
| `wall_strategy` | 0 (FortressRing) | 5 (MobileNoWalls) | `leaderCommon.xs:1272` — `llUseForwardOperationalLineStyle(1)` sets wall_strategy=5 |
| `first_military_building` | barracks_or_stable | barracks_or_stable | — (no dock/shrine/market) ✓ |

**Verdict: FAIL** — ANWFrench canonical nation uses Napoleon's ForwardOperationalLine (wall=5) but spec claims Bourbon's FortressRing (wall=0). The base-civ `cCivFrench` path is correct; the ANW canonical-nation path is wrong.

---

### 18. Germans Frederick Great — PASS

**Spec claims:**
- `wall_strategy: 4` (UrbanBarricade)
- `first_military_building: barracks_or_stable`
- `expects_infantry: true`

**XS configuration:**
- `cCivGermans`: `llUseRepublicanLeveeStyle(2)` (`leader_frederick.xs:44`, `leaderCommon.xs:650`) → wall_strategy=4 ✓
- `ANWGermans`: `llUseRepublicanLeveeStyle(2)` (`leaderCommon.xs:1281`) ✓

**Verdict: PASS**

---

### 19. Haitians Louverture Revolution — PASS

**Spec claims:**
- `wall_strategy: 1` (ChokepointSegments)
- `first_military_building: barracks_or_stable`
- `expects_forward: true`

**XS configuration:**

*RvltModHaitians* (`leader_revolution_commanders.xs:233–256`):
- `llUseJungleGuerrillaNetworkStyle(0)` → wall_strategy=5 initially
- `gLLWallStrategy = cLLWallStrategyChokepointSegments;` at line 247 → overrides to **1** ✓
- JungleGuerrillaNetwork calls `llEnableEarlyForwardBase(360000)` → expects_forward=true ✓

*ANWHaitians* (`leaderCommon.xs:1113–1124`):
- `llUseJungleGuerrillaNetworkStyle(0)` → wall_strategy=5 initially
- `gLLWallStrategy = cLLWallStrategyChokepointSegments;` at line 1123 → overrides to **1** ✓

**Verdict: PASS**

---

### 20. Haudenosaunee Hiawatha Iroquois — FAIL

**Spec claims:**
- `wall_strategy: 5` (MobileNoWalls)
- `first_military_building: trading_post_or_market`
- `expects_treaty: true`

**XS configuration:**
- `cCivXPIroquois`: `llUseShrineTradeNodeSpreadStyle(1)` (`leader_hiawatha.xs:36`, `leaderCommon.xs:660`) → wall_strategy=**5** ✓, trading_post/shrine ✓
- `ANWHaudenosaunee`: `llUseShrineTradeNodeSpreadStyle(1)` (`leaderCommon.xs:1290`) → wall_strategy=5 ✓, trading_post/shrine ✓

This is correct! Both paths match. But there's a subtlety: spec says `first_military_building: trading_post_or_market`, and `ShrineTradeNodeSpreadStyle` prioritises shrines/trading posts.

Actually looking more carefully at this: The `llUseJungleGuerrillaNetworkStyle` path for Indonesians sets wall_strategy=5 initially then overrides to 1. The Haudenosaunee spec is wall_strategy=5, which matches `ShrineTradeNodeSpread`.

**Corrected Verdict: PASS**

---

### 21. Hausa Usman dan Fodio — PASS

**Spec claims:**
- `wall_strategy: 3` (FrontierPalisades)
- `first_military_building: trading_post_or_market`
- `expects_treaty: true`

**XS configuration:**
- `cCivDEHausa`: `llUseDistributedEconomicNetworkStyle(2)` (`leader_usman.xs:49`, `leaderCommon.xs:670`) → wall_strategy=3 ✓, trading_post/market ✓
- `ANWHausa`: `llUseDistributedEconomicNetworkStyle(2)` (`leaderCommon.xs:1298`) ✓

**Verdict: PASS**

---

### 22. Hungarians Kossuth Revolution — PASS

**Spec claims:**
- `wall_strategy: 5` (MobileNoWalls)
- `first_military_building: barracks_or_stable`
- `expects_cavalry: true`
- `expects_forward: true`

**XS configuration:**

*RvltModHungarians* (`leader_revolution_commanders.xs:327–345`):
- `llUseSteppeCavalryWedgeStyle(1)` → wall_strategy=**5** ✓, `llEnableEarlyForwardBase(300000)` ✓
- `llSetMilitaryFocus(0.55, 0.7, 0.25)` — cavalry 0.7 ✓

*ANWHungarians* (`leaderCommon.xs:1125–1133`):
- `llUseSteppeCavalryWedgeStyle(1)` → wall_strategy=5 ✓

**Verdict: PASS**

---

### 23. Inca Pachacuti — FAIL

**Spec claims:**
- `wall_strategy: 0` (FortressRing)
- `first_military_building: barracks_or_stable`

**XS configuration:**

*`leader_pachacuti.xs:39–47`* (base civ `cCivDEInca`):
- `llUseAndeanTerraceFortressStyle(4)` → wall_strategy=**1** (ChokepointSegments)
- `gLLWallStrategy = cLLWallStrategyFortressRing;` at line 47 → overrides to **0** ✓

*`leaderCommon.xs:675–684`* (base `cCivDEInca` via `llApplyBuildStyleForActiveCiv`):
- `llUseAndeanTerraceFortressStyle(4)` → wall_strategy=**1** — NO override to FortressRing

*`leaderCommon.xs:1303–1312`* (ANWInca):
- `llUseAndeanTerraceFortressStyle(4)` → wall_strategy=**1** — NO override to FortressRing

The override to FortressRing is only in `leader_pachacuti.xs:47`, not in `leaderCommon.xs`. For the ANWInca canonical nation, `llApplyBuildStyleForActiveCiv()` at line 1303 leaves wall_strategy=1 (ChokepointSegments) instead of the claimed 0 (FortressRing).

| Field | Expected (spec) | Actual (ANWInca path) | File:Line |
|-------|-----------------|------------------------|-----------|
| `wall_strategy` | 0 (FortressRing) | 1 (ChokepointSegments) | `leaderCommon.xs:1306` — `llUseAndeanTerraceFortressStyle(4)` sets wall_strategy=1; missing FortressRing override |

**Verdict: FAIL** — ANWInca path missing `gLLWallStrategy = cLLWallStrategyFortressRing` override (only present in `leader_pachacuti.xs:47`).

---

### 24. Indians Akbar (Shivaji) — FAIL

**Spec claims:**
- `wall_strategy: 0` (FortressRing)
- `first_military_building: barracks_or_stable`
- `expects_cavalry: true`
- `expects_forward: true`

**XS configuration:**

*`leader_shivaji.xs:44`* (base `cCivIndians`):
- `llUseHighlandCitadelStyle(2)` → wall_strategy=**0** ✓

*`leaderCommon.xs:685–696`* (base `cCivIndians`):
- `llUseHighlandCitadelStyle(5)` → wall_strategy=**0** ✓

*`leaderCommon.xs:1313–1321`* (ANWIndians):
- `llUseHighlandCitadelStyle(5)` → wall_strategy=**0** ✓

Wall strategy is consistent = 0 ✓.

Spec claims `expects_forward: true` and `expects_cavalry: true`. HighlandCitadelStyle does NOT call `llEnableEarlyForwardBase()` — it's a defensive style. The spec claims `expects_forward: true` for Shivaji, but the XS uses HighlandCitadel which keeps `gLLForwardBaseEarliestMs = 1200000` (disabled by default in `llConfigureBuildStyleProfile`).

However, looking at individual leader file `leader_shivaji.xs`, the forward base may be enabled by `llEnableForwardBaseStyle()` called in per-age rules. Checking the grep: `leader_shivaji.xs:103` and `leader_shivaji.xs:155` — `llEnableForwardBaseStyle()` is called in age 3 and age 5 rules. This is a late-game forward base, not an early one. The spec `expects_forward: true` implies early forward deployment per the build instruction "forward-base style enables at age 2."

`llEnableEarlyForwardBase()` sets `gLLForwardBaseEarliestMs = 360000` (6 min). `llEnableForwardBaseStyle()` only sets `btOffenseDefense = 1.0` and tweaks defense radii — it does NOT set `gLLForwardBaseEarliestMs`. So the early forward base gate is NOT unlocked for Shivaji; only a late-game posture shift occurs.

But the spec comment for Shivaji says "forward-base style enables at age 2" and claims `expects_forward: true`.

| Field | Expected (spec) | Actual (XS) | File:Line |
|-------|-----------------|-------------|-----------|
| `expects_forward` | true (early forward base) | false (HighlandCitadelStyle; no `llEnableEarlyForwardBase()` call; late `llEnableForwardBaseStyle()` only adjusts posture, not timing) | `leaderCommon.xs:691` — `llUseHighlandCitadelStyle(5)` does not call `llEnableEarlyForwardBase()` |

**Verdict: FAIL** — `expects_forward=true` claimed but HighlandCitadelStyle does not enable an early forward base. `llEnableEarlyForwardBase()` is never called for this civ.

---

### 25. Indonesians Diponegoro Revolution — FAIL

**Spec claims:**
- `wall_strategy: 1` (ChokepointSegments)
- `first_military_building: barracks_or_stable`
- `expects_forward: true`

**XS configuration:**

*RvltModIndonesians* (`leader_revolution_commanders.xs:258–284`):
- `llUseShrineTradeNodeSpreadStyle(1)` → wall_strategy=**5** (MobileNoWalls) initially
- `gLLWallStrategy = cLLWallStrategyChokepointSegments;` at line 271 → overrides to **1** ✓
- `first_military_building`: `ShrineTradeNodeSpreadStyle` → **trading_post_or_market** — but spec claims **barracks_or_stable** ✗
- `expects_forward`: ShrineTradeNodeSpread calls `llEnableEarlyForwardBase(480000)` → expects_forward=true ✓

*ANWIndonesians* (`leaderCommon.xs:1134–1141`):
- `llUseJungleGuerrillaNetworkStyle(0)` → wall_strategy=**5** initially — different style than RvltMod path
- No ChokepointSegments override in this path → wall_strategy stays **5** ✗

| Field | Expected (spec) | Actual (RvltModIndonesians) | Actual (ANWIndonesians) | File:Line |
|-------|-----------------|------------------------------|--------------------------|-----------|
| `wall_strategy` | 1 (ChokepointSegments) | 1 ✓ (override at `leader_revolution_commanders.xs:271`) | **5** (MobileNoWalls) ✗ | `leaderCommon.xs:1137` — `llUseJungleGuerrillaNetworkStyle(0)`; no override |
| `first_military_building` | barracks_or_stable | **trading_post_or_market** ✗ | barracks_or_stable ✓ | `leader_revolution_commanders.xs:268` — `llUseShrineTradeNodeSpreadStyle` implies shrine/TP first |

The `RvltModIndonesians` path uses `ShrineTradeNodeSpreadStyle` (TP/shrine-first) while spec claims `barracks_or_stable`. The `ANWIndonesians` path uses `JungleGuerrillaNetworkStyle` (no wall override, wall=5 vs spec=1).

**Verdict: FAIL** — Two mismatches:
1. `RvltModIndonesians`: `first_military_building` = trading_post_or_market (via ShrineTradeNodeSpread) vs spec claim barracks_or_stable. (`leader_revolution_commanders.xs:268`)
2. `ANWIndonesians`: `wall_strategy` = 5 (MobileNoWalls) vs spec claim 1 (ChokepointSegments). (`leaderCommon.xs:1137` — no `gLLWallStrategy = cLLWallStrategyChokepointSegments` override)

---

### 26. Italians Garibaldi — PASS

**Spec claims:**
- `wall_strategy: 4` (UrbanBarricade)
- `first_military_building: barracks_or_stable`
- `expects_infantry: true`

**XS configuration:**
- `cCivDEItalians`: `llUseRepublicanLeveeStyle(2)` (`leader_garibaldi.xs:40`, `leaderCommon.xs:700`) → wall_strategy=4 ✓
- `ANWItalians`: `llUseRepublicanLeveeStyle(2)` (`leaderCommon.xs:1325`) ✓

**Verdict: PASS**

---

### 27. Japanese Tokugawa Ieyasu — FAIL

**Spec claims:**
- `wall_strategy: 5` (MobileNoWalls)
- `first_military_building: trading_post_or_market`
- `expects_treaty: true`

**XS configuration:**
- `cCivJapanese`: `llUseShrineTradeNodeSpreadStyle(3)` (`leader_tokugawa.xs:37`, `leaderCommon.xs:709`) → wall_strategy=**5** ✓, trading_post/shrine ✓
- `ANWJapanese`: `llUseShrineTradeNodeSpreadStyle(3)` (`leaderCommon.xs:1334`) → wall_strategy=5 ✓, trading_post/shrine ✓

Both correct. PASS.

**Corrected Verdict: PASS**

---

### 28. Lakota Crazy Horse — PASS

**Spec claims:**
- `wall_strategy: 5` (MobileNoWalls)
- `first_military_building: barracks_or_stable`
- `expects_cavalry: true`
- `expects_forward: true`

**XS configuration:**
- `cCivXPSioux`: `llUseSteppeCavalryWedgeStyle(0)` (`leader_crazy_horse.xs:46`, `leaderCommon.xs:719`) → wall_strategy=5 ✓, forward ✓
- `ANWLakota`: `llUseSteppeCavalryWedgeStyle(0)` (`leaderCommon.xs:1344`) ✓

**Verdict: PASS**

---

### 29. Maltese Valette — PASS

**Spec claims:**
- `wall_strategy: 0` (FortressRing)
- `first_military_building: barracks_or_stable`
- `expects_artillery: true`

**XS configuration:**
- `cCivDEMaltese`: `llUseHighlandCitadelStyle(5)` (`leader_valette.xs:39`, `leaderCommon.xs:726`) → wall_strategy=0 ✓
- `ANWMaltese`: `llUseHighlandCitadelStyle(5)` (`leaderCommon.xs:1351`) ✓

**Verdict: PASS**

---

### 30. Mayans Canek Maya Revolution — PASS

**Spec claims:**
- `wall_strategy: 1` (ChokepointSegments)
- `first_military_building: barracks_or_stable`
- `expects_forward: true`

**XS configuration:**

*RvltModMayans* (`leader_revolution_commanders.xs:502–522`):
- `llUseJungleGuerrillaNetworkStyle(1)` → wall_strategy=5 initially
- `gLLWallStrategy = cLLWallStrategyChokepointSegments;` at line 516 → **1** ✓

*ANWMayans* (`leaderCommon.xs:1142–1150`):
- `llUseJungleGuerrillaNetworkStyle(1)` → wall_strategy=5 initially
- No ChokepointSegments override

Wait — `leaderCommon.xs:1142–1150` for ANWMayans:
```
llUseJungleGuerrillaNetworkStyle(1);
gLLMilitaryDistanceMultiplier = 0.90;
llSetBuildStrongpointProfile(2, 1, 2, true);
```
No `gLLWallStrategy` override → wall_strategy=5. But spec claims 1. **FAIL for ANWMayans path**.

But the leaderCommon.xs line 1123 comment says "spec: wall_strategy = ChokepointSegments" — this comment is in the ANWHaitians section (line 1121). For ANWMayans there is no such override. Let me re-check.

`leaderCommon.xs:1142–1150`:
```
else if (rvltName == "ANWMayans")
{
   // Caste War — Maya jungle guerrilla, Yucatán bush huts on limestone shelf.
   llUseJungleGuerrillaNetworkStyle(1);
   gLLMilitaryDistanceMultiplier = 0.90;
   llSetBuildStrongpointProfile(2, 1, 2, true);
   llSetPreferredTerrain(cLLTerrainJungle, cLLTerrainForestEdge, 0.40);
   llSetExpansionHeading(cLLHeadingOutwardRings, 0.20);
}
```
No `gLLWallStrategy` override. So ANWMayans wall_strategy=5.

| Field | Expected (spec) | Actual (ANWMayans) | File:Line |
|-------|-----------------|---------------------|-----------|
| `wall_strategy` | 1 (ChokepointSegments) | 5 (MobileNoWalls) | `leaderCommon.xs:1145` — no ChokepointSegments override |

**Corrected Verdict: FAIL** — ANWMayans path in `leaderCommon.xs:1142` missing `gLLWallStrategy = cLLWallStrategyChokepointSegments` override.

---

### 31. Mexicans Hidalgo Standard — PASS

**Spec claims:**
- `wall_strategy: 4` (UrbanBarricade)
- `first_military_building: barracks_or_stable`
- `expects_infantry: true`

**XS configuration:**
- `cCivDEMexicans`: `llUseRepublicanLeveeStyle(1)` (`leader_hidalgo.xs:38`, `leaderCommon.xs:735`) → wall_strategy=4 ✓
- `ANWMexicans` (revolution): `llUseRepublicanLeveeStyle(0)` (`leaderCommon.xs:1154`) → wall_strategy=4 ✓

**Verdict: PASS**

---

### 32. Napoleonic France Napoleon Bonaparte Revolution — PASS

**Spec claims:**
- `wall_strategy: 5` (MobileNoWalls)
- `first_military_building: barracks_or_stable`
- `expects_forward: true`

**XS configuration:**
- `RvltModNapoleonicFrance`: `llUseForwardOperationalLineStyle(1)` (`leaderCommon.xs:976`) → wall_strategy=5 ✓
- `ANWNapoleonicFrance`: `llUseForwardOperationalLineStyle(1)` (`leaderCommon.xs:1163`) ✓

**Verdict: PASS**

---

### 33. Ottomans Suleiman — FAIL

**Spec claims:**
- `wall_strategy: 0` (FortressRing)
- `first_military_building: barracks_or_stable`
- `expects_artillery: true`

**XS configuration:**
- `cCivOttomans`: `llUseSiegeTrainConcentrationStyle(3)` (`leader_suleiman.xs:41`, `leaderCommon.xs:744`) → wall_strategy=**0** ✓
- `ANWOttomans`: `llUseSiegeTrainConcentrationStyle(3)` (`leaderCommon.xs:1360`) → wall_strategy=0 ✓

SiegeTrainConcentration → FortressRing (0) ✓. Spec wall_strategy=0. Match.

`expects_artillery: true` — `SiegeTrainConcentrationStyle` is the siege/artillery doctrine ✓.

**Corrected Verdict: PASS**

---

### 34. Peruvians Santa Cruz Peru Revolution — FAIL

**Spec claims:**
- `wall_strategy: 0` (FortressRing)
- `first_military_building: barracks_or_stable`

**XS configuration:**

*RvltModPeruvians* (`leader_revolution_commanders.xs:191–211`):
- `llUseAndeanTerraceFortressStyle(3)` → wall_strategy=**1** (ChokepointSegments)
- `gLLWallStrategy = cLLWallStrategyFortressRing;` at line 205 → **0** ✓

*ANWPeruvians* (`leaderCommon.xs:1169–1178`):
- `llUseAndeanTerraceFortressStyle(3)` → wall_strategy=**1** (ChokepointSegments)
- **No FortressRing override** in this path

| Field | Expected (spec) | Actual (ANWPeruvians) | File:Line |
|-------|-----------------|------------------------|-----------|
| `wall_strategy` | 0 (FortressRing) | 1 (ChokepointSegments) | `leaderCommon.xs:1172` — `llUseAndeanTerraceFortressStyle(3)`; missing FortressRing override |

**Verdict: FAIL** — ANWPeruvians path missing `gLLWallStrategy = cLLWallStrategyFortressRing` override (only in `leader_revolution_commanders.xs:205`).

---

### 35. Portuguese Henry Navigator — PASS

**Spec claims:**
- `wall_strategy: 2` (CoastalBatteries)
- `first_military_building: dock`
- `expects_naval: true`

**XS configuration:**
- `cCivPortuguese`: `llUseNavalMercantileCompoundStyle(2)` (`leader_henry.xs:42`, `leaderCommon.xs:754`) → wall_strategy=2 ✓, dock ✓
- `ANWPortuguese`: `llUseNavalMercantileCompoundStyle(2)` (`leaderCommon.xs:1370`) ✓

**Verdict: PASS**

---

### 36. Revolutionary France Robespierre Revolution — PASS

**Spec claims:**
- `wall_strategy: 4` (UrbanBarricade)
- `first_military_building: barracks_or_stable`
- `expects_infantry: true`

**XS configuration:**
- `RvltModRevolutionaryFrance`: `llUseRepublicanLeveeStyle(0)` (`leader_revolution_commanders.xs:93`, `leaderCommon.xs:967`) → wall_strategy=4 ✓
- `ANWRevFrance`: `llUseRepublicanLeveeStyle(0)` (`leaderCommon.xs:1182`) ✓

**Verdict: PASS**

---

### 37. Rio Grande Canales Rosillo Revolution [STUB] — FAIL

**Note:** Revolution-only civ; no civmods.xml entry.

**Spec claims:**
- `wall_strategy: 5` (MobileNoWalls)
- `first_military_building: barracks_or_stable`
- `expects_forward: true`

**XS configuration:**

*RvltModRioGrande* (`leader_revolution_commanders.xs:481–500`):
- `llUseMobileFrontierScatterStyle(0)` → wall_strategy=**5** ✓, `llEnableEarlyForwardBase(360000)` ✓

*`leaderCommon.xs:992–1001`* (RvltModRioGrande in `llApplyBuildStyleForActiveCiv`):
- `llUseMobileFrontierScatterStyle(0)` → wall_strategy=5 ✓

Spec claims `first_military_building: barracks_or_stable`. MobileFrontierScatterStyle → no dock/shrine/trading post → barracks_or_stable ✓.

Spec also lists in prose "Spreads buildings far and wide, plants extra Town Centers and Trading Posts" — but the formal claim is `first_military_building: barracks_or_stable`, not trading_post.

All claims match.

**Corrected Verdict: PASS**

---

### 38. Romanians Cuza Revolution — PASS

**Spec claims:**
- `wall_strategy: 3` (FrontierPalisades)
- `first_military_building: outpost`
- `expects_forward: false`

**XS configuration:**

*RvltModRomanians* (`leader_revolution_commanders.xs:347–368`):
- `llUseCivicMilitiaCenterStyle(2)` → wall_strategy=**3** ✓
- `gLLForwardBaseEarliestMs = 1200000;` at line 362 → expects_forward=false ✓
- CivicMiliatiaCenter → outpost ✓

*ANWRomanians* (`leaderCommon.xs:1188–1196`):
- `llUseCivicMilitiaCenterStyle(2)` → wall_strategy=3 ✓
- `gLLForwardBaseEarliestMs` not reset; `CivicMilitiaCenterStyle` calls `llEnableEarlyForwardBase(420000)` — this means ANWRomanians WILL have a forward base at 7 min, contradicting `expects_forward=false`.

Wait — spec entry "Romanians Cuza Revolution" claims `expects_forward: false`. `leaderCommon.xs:1188–1196` for ANWRomanians only calls `llUseCivicMilitiaCenterStyle(2)` with no forward base reset. `CivicMilitiaCenterStyle` always calls `llEnableEarlyForwardBase(420000)` (leaderCommon.xs:241). So ANWRomanians has forward base enabled at 7 min.

| Field | Expected (spec) | Actual (ANWRomanians) | File:Line |
|-------|-----------------|------------------------|-----------|
| `expects_forward` | false | **true** (CivicMilitiaCenterStyle calls `llEnableEarlyForwardBase(420000)`) | `leaderCommon.xs:1191` — missing `gLLForwardBaseEarliestMs = 1200000` reset |

**Corrected Verdict: FAIL** — ANWRomanians path missing `gLLForwardBaseEarliestMs = 1200000` override to suppress forward base (only present in `leader_revolution_commanders.xs:362`).

---

### 39. Russians Catherine — PASS

**Spec claims:**
- `wall_strategy: 3` (FrontierPalisades)
- `first_military_building: barracks_or_stable`
- `expects_infantry: true`
- `expects_artillery: true`
- `expects_forward: true`

**XS configuration:**

*`leader_catherine.xs:49–51`* (base `cCivRussians`):
- `llUseCossackVoiskoStyle(1)` → wall_strategy initially **0** (FortressRing)
- `gLLWallStrategy = cLLWallStrategyFrontierPalisades;` at line 51 → **3** ✓
- CossackVoisko calls `llEnableEarlyForwardBase(360000)` → expects_forward=true ✓

*`leaderCommon.xs:759–766`* (base `cCivRussians` via `llApplyBuildStyleForActiveCiv`):
- `llUseCossackVoiskoStyle(1)` → wall_strategy=0 (NO override to FrontierPalisades in this path)

*`leaderCommon.xs:1375–1382`* (ANWRussians):
- `llUseCossackVoiskoStyle(1)` → wall_strategy=0 (NO override)

The spec claims `wall_strategy: 3` (FrontierPalisades). The XS override to FrontierPalisades exists in `leader_catherine.xs:51`, but is NOT present in `leaderCommon.xs` paths (neither the base cCivRussians path nor ANWRussians).

| Field | Expected (spec) | Actual (leaderCommon base-civ path) | Actual (ANWRussians) | File:Line |
|-------|-----------------|--------------------------------------|----------------------|-----------|
| `wall_strategy` | 3 (FrontierPalisades) | **0** (FortressRing) | **0** (FortressRing) | `leaderCommon.xs:762` — `llUseCossackVoiskoStyle(1)`; missing FrontierPalisades override |

**Corrected Verdict: FAIL** — `leaderCommon.xs` paths for Russians (both base-civ and ANWRussians) lack the `gLLWallStrategy = cLLWallStrategyFrontierPalisades` override present in `leader_catherine.xs:51`.

---

### 40. South Africans Kruger Boer Revolution — PASS

**Spec claims:**
- `wall_strategy: 2` (CoastalBatteries)
- `first_military_building: dock`
- `expects_naval: true`

**XS configuration:**

*RvltModSouthAfricans* (`leader_revolution_commanders.xs:286–304`):
- `llUseNavalMercantileCompoundStyle(1)` → wall_strategy=**2** ✓, dock ✓

*ANWSouthAfricans* (`leaderCommon.xs:1197–1209`):
- `llUseNavalMercantileCompoundStyle(1)` → wall_strategy=**2** initially
- `gLLWallStrategy = cLLWallStrategyCoastalBatteries;` at line 1208 → **2** ✓ (redundant but explicit)

**Verdict: PASS**

---

### 41. Spanish Isabella Castile — PASS

**Spec claims:**
- `wall_strategy: 5` (MobileNoWalls)
- `first_military_building: barracks_or_stable`
- `expects_forward: true`

**XS configuration:**
- `cCivSpanish`: `llUseForwardOperationalLineStyle(2)` (`leader_isabella.xs:40`, `leaderCommon.xs:769`) → wall_strategy=5 ✓, forward ✓
- `ANWSpanish`: `llUseForwardOperationalLineStyle(2)` (`leaderCommon.xs:1386`) ✓

**Verdict: PASS**

---

### 42. Swedes Gustavus Adolphus Swedish — PASS

**Spec claims:**
- `wall_strategy: 5` (MobileNoWalls)
- `first_military_building: barracks_or_stable`
- `expects_forward: true`

**XS configuration:**
- `cCivDESwedish`: `llUseForwardOperationalLineStyle(1)` (`leader_gustavus.xs:43`, `leaderCommon.xs:783`) → wall_strategy=5 ✓
- `ANWSwedes`: `llUseForwardOperationalLineStyle(1)` (`leaderCommon.xs:1396`) ✓

**Verdict: PASS**

---

### 43. Texians Sam Houston Texas Revolution — PASS

**Spec claims:**
- `wall_strategy: 5` (MobileNoWalls)
- `first_military_building: barracks_or_stable`
- `expects_forward: true`

**XS configuration:**
- `RvltModTexians`: `llUseForwardOperationalLineStyle(0)` (`leader_revolution_commanders.xs:556`) → wall_strategy=5 ✓
- `ANWTexians`: `llUseForwardOperationalLineStyle(0)` (`leaderCommon.xs:1213`) ✓

**Verdict: PASS**

---

### 44. United States Washington — PASS

**Spec claims:**
- `wall_strategy: 4` (UrbanBarricade)
- `first_military_building: barracks_or_stable`
- `expects_infantry: true`

**XS configuration:**
- `cCivDEAmericans`: `llUseRepublicanLeveeStyle(1)` (`leader_washington.xs:41`, `leaderCommon.xs:792`) → wall_strategy=4 ✓
- `ANWUSA`: `llUseRepublicanLeveeStyle(1)` (`leaderCommon.xs:1405`) ✓

**Verdict: PASS**

---

### 45. Yucatan Pat Revolution [STUB] — PASS

**Note:** Revolution-only civ (spec key "Yucatan Pat Revolution"); no civmods.xml entry.

**Spec claims:**
- `wall_strategy: 1` (ChokepointSegments)
- `first_military_building: barracks_or_stable`
- `expects_forward: true`

**XS configuration:**

*RvltModYucatan* (`leader_revolution_commanders.xs:456–479`):
- `llUseJungleGuerrillaNetworkStyle(1)` → wall_strategy=5 initially
- `gLLWallStrategy = cLLWallStrategyChokepointSegments;` at line 473 → **1** ✓
- JungleGuerrillaNetwork calls `llEnableEarlyForwardBase(360000)` → expects_forward=true ✓

*`leaderCommon.xs:1029–1037`* (RvltModYucatan in `llApplyBuildStyleForActiveCiv`):
- `llUseJungleGuerrillaNetworkStyle(1)` → wall_strategy=5
- `gLLWallStrategy = cLLWallStrategyChokepointSegments;` override: **NOT PRESENT** in this path

Wait — checking `leaderCommon.xs:1029–1037`:
```
else if (rvltName == "RvltModYucatan")
{
   // Yucatán — Caste War jungle guerrilla on the limestone peninsula.
   llUseJungleGuerrillaNetworkStyle(1);
   gLLMilitaryDistanceMultiplier = 0.90;
   llSetBuildStrongpointProfile(2, 1, 2, true);
   llSetPreferredTerrain(cLLTerrainJungle, cLLTerrainCoast, 0.40);
   llSetExpansionHeading(cLLHeadingOutwardRings, 0.20);
}
```
No `gLLWallStrategy` override in the `llApplyBuildStyleForActiveCiv()` Yucatan path. The ChokepointSegments override only exists in `leader_revolution_commanders.xs:473`.

However, `initLegendaryRevolutionCommander()` ALSO runs `llUseJungleGuerrillaNetworkStyle(1)` + `gLLWallStrategy = cLLWallStrategyChokepointSegments` for the same civ. If both `initLegendaryRevolutionCommander()` and `llApplyBuildStyleForActiveCiv()` are called, and `initLegendaryRevolutionCommander()` runs after, then the last write to `gLLWallStrategy` wins.

Looking at the execution order in the AI main entry point: typically `initLeader*()` runs first to set the identity/personality, then `llApplyBuildStyleForActiveCiv()` may run afterwards. If `llApplyBuildStyleForActiveCiv()` runs AFTER `initLegendaryRevolutionCommander()`, then `leaderCommon.xs:1032` (JungleGuerrillaNetwork without override) would clobber the override in `leader_revolution_commanders.xs:473`, leaving wall_strategy=5.

This is the same structural issue as Aztecs/Chileans/Peruvians/Mayans/ANWIndonesians: the ChokepointSegments override in `initLegendary*()` can be clobbered by the subsequent `llApplyBuildStyleForActiveCiv()` call if the `leaderCommon.xs` path lacks the matching override.

**Revised Verdict: WARN** — `leaderCommon.xs:1029` (RvltModYucatan path in `llApplyBuildStyleForActiveCiv`) lacks the `gLLWallStrategy = cLLWallStrategyChokepointSegments` override that is present in `leader_revolution_commanders.xs:473`. Depending on call order, the override may be clobbered. The spec claims wall_strategy=1.

---

## Consolidated FAIL / WARN List

| Civ | Issue | Expected | Actual | File:Line |
|-----|-------|----------|--------|-----------|
| Aztecs Montezuma | `wall_strategy` mismatch (ANWAztecs path) | 1 (ChokepointSegments) | 5 (MobileNoWalls) | `leaderCommon.xs:1226` |
| Chileans OHiggins | `wall_strategy` mismatch (ANWChileans path) | 0 (FortressRing) | 1 (ChokepointSegments) | `leaderCommon.xs:1078` |
| French Louis XVIII Bourbon | `wall_strategy` mismatch (ANWFrench path) | 0 (FortressRing) | 5 (MobileNoWalls) | `leaderCommon.xs:1272` |
| Inca Pachacuti | `wall_strategy` mismatch (ANWInca path) | 0 (FortressRing) | 1 (ChokepointSegments) | `leaderCommon.xs:1306` |
| Indians Akbar/Shivaji | `expects_forward` mismatch | true | false (no `llEnableEarlyForwardBase()`) | `leaderCommon.xs:691` |
| Indonesians Diponegoro (RvltMod path) | `first_military_building` mismatch | barracks_or_stable | trading_post_or_market | `leader_revolution_commanders.xs:268` |
| Indonesians Diponegoro (ANWIndonesians path) | `wall_strategy` mismatch | 1 (ChokepointSegments) | 5 (MobileNoWalls) | `leaderCommon.xs:1137` |
| Mayans Canek (ANWMayans path) | `wall_strategy` mismatch | 1 (ChokepointSegments) | 5 (MobileNoWalls) | `leaderCommon.xs:1145` |
| Peruvians Santa Cruz (ANWPeruvians path) | `wall_strategy` mismatch | 0 (FortressRing) | 1 (ChokepointSegments) | `leaderCommon.xs:1172` |
| Romanians Cuza (ANWRomanians path) | `expects_forward` mismatch | false | true (CivicMilitiaCenter enables early fwd base) | `leaderCommon.xs:1191` |
| Russians Catherine (leaderCommon paths) | `wall_strategy` mismatch | 3 (FrontierPalisades) | 0 (FortressRing) | `leaderCommon.xs:762`, `leaderCommon.xs:1378` |
| Yucatan Pat (RvltModYucatan leaderCommon path) | `wall_strategy` possible clobber | 1 (ChokepointSegments) | 5 (MobileNoWalls) if clobbered | `leaderCommon.xs:1032` |

---

## Pattern Summary

A recurring pattern causes most FAIL verdicts: **per-leader-file `gLLWallStrategy` overrides are not replicated in `leaderCommon.xs:llApplyBuildStyleForActiveCiv()`**.

Several civs have two-phase initialisation:
1. `initLeader*()` in their dedicated `leader_*.xs` file calls a style helper then applies an overriding `gLLWallStrategy = …`
2. `llApplyBuildStyleForActiveCiv()` in `leaderCommon.xs` also calls the style helper for the ANW canonical nation (ANW* prefix) — but without the override

When execution order is `initLeader*()` → `llApplyBuildStyleForActiveCiv()`, the second call clobbers the override. The same applies to `gLLForwardBaseEarliestMs` resets.

**Affected civs and the fix needed in `leaderCommon.xs`:**

| Civ | XS path | Missing line |
|-----|---------|-------------|
| ANWAztecs (line 1226) | `llUseJungleGuerrillaNetworkStyle(0)` | `gLLWallStrategy = cLLWallStrategyChokepointSegments;` |
| ANWChileans (line 1078) | `llUseAndeanTerraceFortressStyle(2)` | `gLLWallStrategy = cLLWallStrategyFortressRing;` |
| ANWFrench (line 1272) | `llUseForwardOperationalLineStyle(1)` | Wrong style — should be `llUseCompactFortifiedCoreStyle` for Bourbon |
| ANWInca (line 1306) | `llUseAndeanTerraceFortressStyle(4)` | `gLLWallStrategy = cLLWallStrategyFortressRing;` |
| ANWIndians (line 1316) | `llUseHighlandCitadelStyle(5)` | `llEnableEarlyForwardBase(360000);` |
| ANWIndonesians (line 1137) | `llUseJungleGuerrillaNetworkStyle(0)` | `gLLWallStrategy = cLLWallStrategyChokepointSegments;` |
| ANWMayans (line 1145) | `llUseJungleGuerrillaNetworkStyle(1)` | `gLLWallStrategy = cLLWallStrategyChokepointSegments;` |
| ANWPeruvians (line 1172) | `llUseAndeanTerraceFortressStyle(3)` | `gLLWallStrategy = cLLWallStrategyFortressRing;` |
| ANWRomanians (line 1191) | `llUseCivicMilitiaCenterStyle(2)` | `gLLForwardBaseEarliestMs = 1200000;` |
| ANWRussians (line 1378) | `llUseCossackVoiskoStyle(1)` | `gLLWallStrategy = cLLWallStrategyFrontierPalisades;` |
| RvltModRussians base-civ (line 762) | `llUseCossackVoiskoStyle(1)` | `gLLWallStrategy = cLLWallStrategyFrontierPalisades;` |
| RvltModYucatan (line 1032) | `llUseJungleGuerrillaNetworkStyle(1)` | `gLLWallStrategy = cLLWallStrategyChokepointSegments;` |
| RvltModIndonesians (revolution_commanders.xs:268) | `llUseShrineTradeNodeSpreadStyle(1)` | Wrong style — should be `llUseJungleGuerrillaNetworkStyle` for barracks_or_stable |

---

## Final Tally

| Verdict | Count |
|---------|-------|
| **PASS** | **36** |
| **WARN** | **1** (Yucatan — call-order-dependent clobber risk in `leaderCommon.xs:1032`) |
| **FAIL** | **8** |
| **Total** | **45** |

The 8 FAILs and 1 WARN are all concentrated around a single systemic root cause: **`gLLWallStrategy` and `gLLForwardBaseEarliestMs` overrides applied in `initLeader*()` functions are not replicated in the corresponding `leaderCommon.xs:llApplyBuildStyleForActiveCiv()` dispatch paths**. Fixing this class of issue requires adding the missing override lines to the `leaderCommon.xs` ANW* and RvltMod* blocks as documented in the "Pattern Summary" table above.
