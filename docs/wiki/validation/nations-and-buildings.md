# Nations and Buildings Map

> Canonical reference for all ANW civ tokens, their culture group, and their building rosters.
>
> Sources:
> - [`artifacts/validation/per_civ_building_capture_map.json`](../../../artifacts/validation/per_civ_building_capture_map.json) — generated 2026-06-07
> - [`artifacts/validation/per_civ_building_checklist.md`](../../../artifacts/validation/per_civ_building_checklist.md) — generated 2026-06-07
> - [`data/civmods.xml`](../../../data/civmods.xml) — canonical civ-token list (`<name>` field per civ entry)

---

## Civ Token → Culture Table

44 ANW civ tokens sourced from `data/civmods.xml` `<name>` fields. Culture sourced from `<culture>` field via `per_civ_building_capture_map.json`.

| ANW Token | Culture | Screenshot baseline |
|-----------|---------|-------------------|
| ANWBritish | WesternEurope | Present (`artifacts/visual_art/ANWBritish/`) |
| ANWFrench | WesternEurope | Present |
| ANWDutch | WesternEurope | Present |
| ANWUSA | WesternEurope | Present |
| ANWCanadians | WesternEurope | Present |
| ANWNapoleonicFrance | WesternEurope | Present |
| ANWRevFrance | WesternEurope | Present |
| ANWHaitians | WesternEurope | Present |
| ANWIndonesians | WesternEurope | Present |
| ANWSouthAfricans | WesternEurope | Present |
| ANWSpanish | Mediterranean | Present |
| ANWPortuguese | Mediterranean | Present |
| ANWOttomans | Mediterranean | Present |
| ANWItalians | Mediterranean | Present |
| ANWMaltese | Mediterranean | Present |
| ANWBrazil | Mediterranean | Present |
| ANWArgentines | Mediterranean | Present |
| ANWChileans | Mediterranean | Present |
| ANWPeruvians | Mediterranean | Present |
| ANWColumbians | Mediterranean | Present |
| ANWMexicans | Mediterranean | Present |
| ANWCalifornians | Mediterranean | Present |
| ANWCentralAmericans | Mediterranean | Present |
| **ANWBajaCalifornians** | Mediterranean | **ZERO captured screenshots** |
| **ANWRioGrande** | Mediterranean | **ZERO captured screenshots** |
| ANWBarbary | Mediterranean | Present |
| ANWEgyptians | Mediterranean | Present |
| ANWMayans | Mediterranean | Present |
| ANWTexians | Mediterranean | Present |
| ANWRussians | EasternEurope | Present |
| ANWGermans | EasternEurope | Present |
| ANWSwedes | EasternEurope | Present |
| ANWFinnish | EasternEurope | Present |
| ANWHungarians | EasternEurope | Present |
| ANWRomanians | EasternEurope | Present |
| ANWAztecs | Aztec | Present |
| ANWChinese | Chinese | Present |
| ANWEthiopians | AfricaEast | Present |
| ANWHausa | AfricaWest | Present |
| ANWInca | Inca | Present |
| ANWIndians | Indian | Present |
| ANWHaudenosaunee | Iroquois | Present |
| ANWJapanese | Japanese | Present |
| ANWLakota | Sioux | Present |

> **Screenshot baseline note:** "Present" means a directory exists under `artifacts/visual_art/ANW<Token>/`. `ANWBajaCalifornians` and `ANWRioGrande` have no directory there and zero visual-art captures. They do have AI-matrix test screenshots under `artifacts/anw_matrix/` but those are AI-behaviour probe images, not the canonical art/surface captures.

---

## Culture → Building Roster Templates

12 culture templates, sourced from `per_civ_building_capture_map.json` `cultures` section.

### WesternEurope

10 ANW civs: British, French, Dutch, USA, Canadians, NapoleonicFrance, RevFrance, Haitians, Indonesians, SouthAfricans.

| Building | Proto | Age available |
|----------|-------|--------------|
| Town Center | `TownCenter` | 1 |
| Barracks | `Barracks` | 1 |
| Stable | `Stable` | 1 |
| Artillery Foundry | `ArtilleryDepot` | 1 |
| Dock | `Dock` | 1 |
| Church | `Church` | 1 |
| Market | `Market` | 1 |
| Trading Post | `TradingPost` | 1 |
| Outpost | `Outpost` | 1 |
| Fort | `FortFrontier` | 3 |
| Capitol | `Capitol` | 4 |

### Mediterranean

19 ANW civs: Spanish, Portuguese, Ottomans, Italians, Maltese, Brazil, Argentines, Chileans, Peruvians, Columbians, Mexicans, Californians, CentralAmericans, BajaCalifornians, RioGrande, Barbary, Egyptians, Mayans, Texians.

| Building | Proto | Age available |
|----------|-------|--------------|
| Town Center | `TownCenter` | 1 |
| Barracks | `Barracks` | 1 |
| Stable | `Stable` | 1 |
| Artillery Foundry | `ArtilleryDepot` | 1 |
| Dock | `Dock` | 1 |
| Church | `Church` | 1 |
| Market | `Market` | 1 |
| Trading Post | `TradingPost` | 1 |
| Outpost | `Outpost` | 1 |
| Fort | `FortFrontier` | 3 |
| Capitol | `Capitol` | 4 |

### EasternEurope

6 ANW civs: Russians, Germans, Swedes, Finnish, Hungarians, Romanians.

| Building | Proto | Age available |
|----------|-------|--------------|
| Town Center | `TownCenter` | 1 |
| Barracks | `Barracks` | 1 |
| Stable | `Stable` | 1 |
| Artillery Foundry | `ArtilleryDepot` | 1 |
| Dock | `Dock` | 1 |
| Church | `Church` | 1 |
| Market | `Market` | 1 |
| Trading Post | `TradingPost` | 1 |
| Outpost | `Outpost` | 1 |
| Fort | `FortFrontier` | 3 |
| Capitol | `Capitol` | 4 |

### Aztec

1 ANW civ: ANWAztecs.

| Building | Proto | Age available |
|----------|-------|--------------|
| Town Center | `TownCenter` | 1 |
| War Hut | `WarHut` | 1 |
| Nobles' Hut | `NoblesHut` | 1 |
| Trading Post | `TradingPost` | 1 |
| Dock | `Dock` | 1 |
| Market | `Market` | 1 |

### Chinese

1 ANW civ: ANWChinese.

| Building | Proto | Age available |
|----------|-------|--------------|
| Town Center | `TownCenter` | 1 |
| Wonder (age-up) | base-game wonder set (player-selected) | age-up |
| Monastery | `ypMonastery` | 1 |
| Castle | `ypCastle` | 1 |
| Consulate | `ypConsulate` | 1 |
| Dock (Asian) | `YPDockAsian` | 1 |
| Trade Market (Asian) | `ypTradeMarketAsian` | 1 |
| War Academy | `ypWarAcademy` | 1 |
| Trading Post | `TradingPost` | 1 |

> NOTE: Asian civs age up by building a Wonder, choosing one of several base-game Wonder protounits from the `YPAge0ChineseWonders` set at each age-up. These Wonders are base-game protounits resolved at runtime; ANW defines **no** Wonder protos of its own (zero Wonder entries in `data/protomods.xml`), so there is no mod-specific proto to list here — the proto field is null because there is nothing for the mod to override, not because extraction is incomplete.

### Indian

1 ANW civ: ANWIndians.

| Building | Proto | Age available |
|----------|-------|--------------|
| Town Center | `TownCenter` | 1 |
| Wonder (age-up) | base-game wonder set (player-selected) | age-up |
| Monastery | `ypMonastery` | 1 |
| Castle | `ypCastle` | 1 |
| Consulate | `ypConsulate` | 1 |
| Barracks (Indian) | `YPBarracksIndian` | 1 |
| Dock (Asian) | `YPDockAsian` | 1 |
| Trade Market (Asian) | `ypTradeMarketAsian` | 1 |
| Caravanserai | `ypCaravanserai` | 1 |
| Trading Post | `TradingPost` | 1 |

> NOTE: Asian civs age up by building a Wonder, choosing one of several base-game Wonder protounits from the `ypAge0IndiansWonders` set at each age-up. These Wonders are base-game protounits resolved at runtime; ANW defines **no** Wonder protos of its own (zero Wonder entries in `data/protomods.xml`), so there is no mod-specific proto to list here — the proto field is null because there is nothing for the mod to override, not because extraction is incomplete.

### Japanese

1 ANW civ: ANWJapanese.

| Building | Proto | Age available |
|----------|-------|--------------|
| Town Center | `TownCenter` | 1 |
| Wonder (age-up) | base-game wonder set (player-selected) | age-up |
| Monastery | `ypMonastery` | 1 |
| Castle | `ypCastle` | 1 |
| Consulate | `ypConsulate` | 1 |
| Barracks (Japanese) | `ypBarracksJapanese` | 1 |
| Stable (Japanese) | `ypStableJapanese` | 1 |
| Dock (Asian) | `YPDockAsian` | 1 |
| Trade Market (Asian) | `ypTradeMarketAsian` | 1 |
| Dojo | `ypDojo` | 1 |
| Trading Post | `TradingPost` | 1 |

> NOTE: Asian civs age up by building a Wonder, choosing one of several base-game Wonder protounits from the `YPAge0JapaneseWonders` set at each age-up. These Wonders are base-game protounits resolved at runtime; ANW defines **no** Wonder protos of its own (zero Wonder entries in `data/protomods.xml`), so there is no mod-specific proto to list here — the proto field is null because there is nothing for the mod to override, not because extraction is incomplete.

### Iroquois

1 ANW civ: ANWHaudenosaunee.

| Building | Proto | Age available |
|----------|-------|--------------|
| Town Center | `TownCenter` | 1 |
| War Hut | `WarHut` | 1 |
| Longhouse | `Longhouse` | 1 |
| Corral | `Corral` | 1 |
| Artillery Depot | `ArtilleryDepot` | 1 |
| Trading Post | `TradingPost` | 1 |
| Dock | `Dock` | 1 |
| Market | `Market` | 1 |

### Sioux

1 ANW civ: ANWLakota.

| Building | Proto | Age available |
|----------|-------|--------------|
| Town Center | `TownCenter` | 1 |
| War Hut | `WarHut` | 1 |
| Corral | `Corral` | 1 |
| Community Plaza | `CommunityPlaza` | 1 |
| Trading Post | `TradingPost` | 1 |
| Dock | `Dock` | 1 |
| Market | `Market` | 1 |

### Inca

1 ANW civ: ANWInca.

| Building | Proto | Age available |
|----------|-------|--------------|
| Town Center | `TownCenter` | 1 |
| Kallanka | `deKallanka` | 1 |
| War Hut | `WarHut` | 1 |
| Community Plaza | `CommunityPlaza` | 1 |
| Trading Post | `TradingPost` | 1 |
| Dock | `Dock` | 1 |
| Market | `Market` | 1 |
| Inca Stronghold | `deIncaStronghold` | 3 |

### AfricaEast

1 ANW civ: ANWEthiopians.

| Building | Proto | Age available |
|----------|-------|--------------|
| Town Center | `TownCenter` | 1 |
| War Camp | `deWarCamp` | 1 |
| Granary | `deGranary` | 1 |
| Tower | `deTower` | 1 |
| Port | `dePort` | 1 |
| Livestock Market | `deLivestockMarket` | 1 |
| Palace | `dePalace` | 1 |
| Mountain Monastery | `deMountainMonastery` | 1 |
| Trading Post | `TradingPost` | 1 |

### AfricaWest

1 ANW civ: ANWHausa.

| Building | Proto | Age available |
|----------|-------|--------------|
| Town Center | `TownCenter` | 1 |
| War Camp | `deWarCamp` | 1 |
| Granary | `deGranary` | 1 |
| Tower | `deTower` | 1 |
| Port | `dePort` | 1 |
| Livestock Market | `deLivestockMarket` | 1 |
| Palace | `dePalace` | 1 |
| University | `deUniversity` | 1 |
| Trading Post | `TradingPost` | 1 |

---

## Per-Civ Building Overrides

Buildings that differ from or extend the culture template. Sourced from `per_civ_building_capture_map.json` `civs` section.

| ANW Token | Override / addition | Proto | Source note |
|-----------|--------------------|----|-------------|
| ANWBritish | + Manor | `Manor` | `Age0British` l.676 |
| ANWDutch | + Bank | `Bank` | `Age0Dutch` l.902 |
| ANWUSA | Church → Meeting House; Capitol → State Capitol; + Saloon | `Church` / `deStateCapitol` / `Saloon` | `DEAge0Americans` l.83598–83724 |
| ANWCanadians | + Manor | `Manor` | `ANWAge0Canadians` techtreemods.xml l.1027 |
| ANWSouthAfricans | + Manor | `Manor` | `ANWAge0SouthAfricans`; Bank available via HC card but not at game start |
| ANWOttomans | Church → Mosque (visual skin) | `Church` (proto) | `Age0Ottoman` l.1543; `DECivHasMosque` applies visual |
| ANWArgentines | + Hacienda | `deHacienda` | `ANWAge0Argentines` techtreemods.xml l.1539 |
| ANWChileans | + Hacienda | `deHacienda` | `ANWAge0Chileans` (Python scan) |
| ANWPeruvians | + Hacienda | `deHacienda` | `ANWAge0Peruvians` techtreemods.xml l.2474 |
| ANWColumbians | + Hacienda | `deHacienda` | `ANWAge0Columbians` techtreemods.xml l.2119 |
| ANWMexicans | + Hacienda; + Saloon | `deHacienda` / `Saloon` | `ANWAge0Mexicans` techtreemods.xml l.680, l.668 |
| ANWCalifornians | + Hacienda; + Saloon | `deHacienda` / `Saloon` | `civmods.xml` Age0 = `DEAge0Mexicans` |
| ANWCentralAmericans | + Hacienda; + Saloon | `deHacienda` / `Saloon` | `civmods.xml` Age0 = `DEAge0Mexicans` |
| ANWBajaCalifornians | + Hacienda; + Saloon | `deHacienda` / `Saloon` | `civmods.xml` Age0 = `DEAge0Mexicans` |
| ANWRioGrande | + Hacienda; + Saloon | `deHacienda` / `Saloon` | `civmods.xml` Age0 = `DEAge0Mexicans` |
| ANWBarbary | Church → Mosque | `Church` (proto) | `ANWAge0Barbary` activates `DECivHasMosque` (techtreemods.xml ~l.5522) → Mosque visual skin, same path as Ottomans/Egyptians |
| ANWEgyptians | Church → Mosque | `Church` (proto) | `ANWAge0Egypt` techtreemods.xml l.5932 activates `DECivHasMosque` |
| ANWMayans | + War Hut; + Hacienda | `WarHut` / `deHacienda` | `ANWAge0Maya` techtreemods.xml l.6194; both granted by explicit `Enable` effects (WarHut multiple; `deHacienda` Enable ~l.6461) — not HC-card-only |
| ANWTexians | + Hacienda | `deHacienda` | `ANWAge0Texas` techtreemods.xml l.7108 |
| ANWRussians | + Blockhouse | `Blockhouse` | `Age0Russian` l.587–596 |
| ANWSwedes | + Torp | `deTorp` | Base-game Swedish signature building via `DEAge0Swedish` (unchanged by mod); corroborated by sibling `ANWAge0Finnish` (shares Swedish age-up chain) enabling `deTorp` at techtreemods.xml l.4072 |

---

## Wall Strategy Index

All 44 active ANW civs have an **explicit** wall strategy (the gated
`anw_wall_strategy_coverage` validator proves none silently falls through to the
engine default). The values below are cross-validated: the `wall_strategy` claim
in `playstyle_spec.json` matches the strategy derived from the AI XS dispatch in
`artifacts/validation/ai_behaviour_map.json` for all 44 civs (0 mismatches). The
gated `per_civ_wall_knobs` validator additionally pins the radius/gate/segment
knobs for the 18 civs that customise them; the remaining civs use the per-strategy
defaults.

Strategy enum (`game/ai/aiHeader.xs` → `cANWWallStrategy*`):

| # | Name | Behaviour |
|---|------|-----------|
| 0 | FortressRing | Full double ring, all sides |
| 1 | ChokepointSegments | Segment walls at terrain pinches (real chokepoint detection) |
| 2 | CoastalBatteries | Land-side ring, gun towers / batteries at the coast |
| 3 | FrontierPalisades | Quick wooden ring + blockhouses |
| 4 | UrbanBarricade | Tight compact inner ring + towers |
| 5 | MobileNoWalls | Scouts + outposts, no walls |

| ANW Token | # | Strategy |
|-----------|---|----------|
| ANWArgentines | 5 | MobileNoWalls |
| ANWAztecs | 1 | ChokepointSegments |
| ANWBajaCalifornians | 2 | CoastalBatteries |
| ANWBarbary | 2 | CoastalBatteries |
| ANWBrazil | 3 | FrontierPalisades |
| ANWBritish | 2 | CoastalBatteries |
| ANWCalifornians | 5 | MobileNoWalls |
| ANWCanadians | 0 | FortressRing |
| ANWCentralAmericans | 3 | FrontierPalisades |
| ANWChileans | 0 | FortressRing |
| ANWChinese | 0 | FortressRing |
| ANWColumbians | 5 | MobileNoWalls |
| ANWDutch | 2 | CoastalBatteries |
| ANWEgyptians | 0 | FortressRing |
| ANWEthiopians | 0 | FortressRing |
| ANWFinnish | 0 | FortressRing |
| ANWFrench | 0 | FortressRing |
| ANWGermans | 4 | UrbanBarricade |
| ANWHaitians | 1 | ChokepointSegments |
| ANWHaudenosaunee | 5 | MobileNoWalls |
| ANWHausa | 3 | FrontierPalisades |
| ANWHungarians | 5 | MobileNoWalls |
| ANWInca | 0 | FortressRing |
| ANWIndians | 0 | FortressRing |
| ANWIndonesians | 1 | ChokepointSegments |
| ANWItalians | 4 | UrbanBarricade |
| ANWJapanese | 5 | MobileNoWalls |
| ANWLakota | 5 | MobileNoWalls |
| ANWMaltese | 0 | FortressRing |
| ANWMayans | 1 | ChokepointSegments |
| ANWMexicans | 4 | UrbanBarricade |
| ANWNapoleonicFrance | 5 | MobileNoWalls |
| ANWOttomans | 0 | FortressRing |
| ANWPeruvians | 0 | FortressRing |
| ANWPortuguese | 2 | CoastalBatteries |
| ANWRevFrance | 4 | UrbanBarricade |
| ANWRioGrande | 3 | FrontierPalisades |
| ANWRomanians | 3 | FrontierPalisades |
| ANWRussians | 3 | FrontierPalisades |
| ANWSouthAfricans | 2 | CoastalBatteries |
| ANWSpanish | 5 | MobileNoWalls |
| ANWSwedes | 5 | MobileNoWalls |
| ANWTexians | 5 | MobileNoWalls |
| ANWUSA | 4 | UrbanBarricade |

---

## Screenshot Coverage Notes

- **ANWBajaCalifornians**: ZERO baseline art captures. No directory under `artifacts/visual_art/`. Has AI-matrix probe screenshots only (under `artifacts/anw_matrix/`).
- **ANWRioGrande**: ZERO baseline art captures. Same situation as BajaCalifornians.
- All other 42 ANW civs have at least one directory entry under `artifacts/visual_art/`.

---

## Cross-references

- [`data/civmods.xml`](../../../data/civmods.xml) — canonical civ-token source
- [`artifacts/validation/per_civ_building_capture_map.json`](../../../artifacts/validation/per_civ_building_capture_map.json) — culture templates + per-civ building lists
- [`artifacts/validation/per_civ_building_checklist.md`](../../../artifacts/validation/per_civ_building_checklist.md) — capture checklist for screenshot pipeline
- [`data-layer/civmods.md`](../data-layer/civmods.md) — civmods.xml schema
- [UI Surfaces](ui-surfaces.md) — coordinates used for capture
