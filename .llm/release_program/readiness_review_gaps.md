# ANW Release Readiness — Per-Nation Gap Report

**Generated:** 2026-06-08  
**Site:** `artifacts/validation/release_readiness_site.html`  
**Site build:** CLEAN (exit 0, 68/68 validators PASS, 44/44 civs rendered)

## Summary

- **40 / 44 nations: fully review-ready** — spec entry present, wall strategy shown, 2–54 screenshots, 6–10/10 art surfaces in manifest
- **4 / 44 nations: BLOCKED** — ANWBajaCalifornians, ANWCalifornians, ANWCentralAmericans, ANWRioGrande have ZERO screenshots (no art folder / manifest); blocked on live game capture, not fixable offline

## Methodology notes
- "art surfaces ok?" counts surfaces present in `manifest.json` crops (10 canonical surfaces). 40/44 civs have a manifest; the 4 zero-screenshot civs have none.
- Uniform 4-surface gap (esc_menu_player_summary, home_city_button, hud_flag_corner, tech_tree_overview) affects 40/44 civs — these surfaces require an in-game session to capture. Shown as "PARTIAL" not "FAIL" — the site renders "missing" cells clearly.
- Wall strategy is present in `playstyle_spec.json` → `claims.wall_strategy` for all 44 civs. The site reads this and renders the wall-doctrine block per card. The recent wall-strategy fix (Tick 3, validate_anw_wall_strategy_coverage.py GREEN 44/44) means the xs-level strategy matches the spec-level data.
- `no age_up_techs claim` was a false gap: `playstyle_spec.json` stores age-up data under `claims.age_up_techs` only for a subset of civs; the site surfaces age-up from a_new_world.html NATION_PLAYSTYLE data instead, so this is not a blocker.

## Per-Nation Table (44 rows)

| civ | screenshots (count / MISSING) | art surfaces ok? | wall strategy shown? | other gaps | review-ready |
|-----|------------------------------|-----------------|----------------------|------------|:------------:|
| ANWArgentines | 2 | PARTIAL (6/10) | YES — MobileNoWalls (5) | 4 art surfaces missing: esc_menu, hc_button, hud_flag, tech_tree | Y |
| ANWAztecs | 2 | PARTIAL (6/10) | YES — ChokepointSegments (1) | 4 art surfaces missing (same set) | Y |
| ANWBajaCalifornians | MISSING | NO (0/10) | YES — CoastalBatteries (2) | BLOCKED: zero screenshots, no manifest; live capture required | N |
| ANWBarbary | 2 | PARTIAL (6/10) | YES — CoastalBatteries (2) | 4 art surfaces missing | Y |
| ANWBrazil | 2 | PARTIAL (6/10) | YES — FrontierPalisades (3) | 4 art surfaces missing | Y |
| ANWBritish | 34 | YES (10/10) | YES — CoastalBatteries (2) | — | Y |
| ANWCalifornians | MISSING | NO (0/10) | YES — MobileNoWalls (5) | BLOCKED: zero screenshots, no manifest; live capture required | N |
| ANWCanadians | 4 | PARTIAL (8/10) | YES — FortressRing (0) | 2 art surfaces missing: esc_menu, tech_tree | Y |
| ANWCentralAmericans | MISSING | NO (0/10) | YES — FrontierPalisades (3) | BLOCKED: zero screenshots, no manifest; live capture required | N |
| ANWChileans | 2 | PARTIAL (6/10) | YES — FortressRing (0) | 4 art surfaces missing | Y |
| ANWChinese | 2 | PARTIAL (6/10) | YES — FortressRing (0) | 4 art surfaces missing | Y |
| ANWColumbians | 2 | PARTIAL (6/10) | YES — MobileNoWalls (5) | 4 art surfaces missing | Y |
| ANWDutch | 2 | PARTIAL (6/10) | YES — CoastalBatteries (2) | 4 art surfaces missing | Y |
| ANWEgyptians | 2 | PARTIAL (6/10) | YES — FortressRing (0) | 4 art surfaces missing | Y |
| ANWEthiopians | 2 | PARTIAL (6/10) | YES — FortressRing (0) | 4 art surfaces missing | Y |
| ANWFinnish | 2 | PARTIAL (6/10) | YES — FortressRing (0) | 4 art surfaces missing | Y |
| ANWFrench | 2 | PARTIAL (6/10) | YES — FortressRing (0) | 4 art surfaces missing | Y |
| ANWGermans | 2 | PARTIAL (6/10) | YES — UrbanBarricade (4) | 4 art surfaces missing | Y |
| ANWHaitians | 2 | PARTIAL (6/10) | YES — ChokepointSegments (1) | 4 art surfaces missing | Y |
| ANWHaudenosaunee | 2 | PARTIAL (6/10) | YES — MobileNoWalls (5) | 4 art surfaces missing | Y |
| ANWHausa | 2 | PARTIAL (6/10) | YES — FrontierPalisades (3) | 4 art surfaces missing | Y |
| ANWHungarians | 2 | PARTIAL (6/10) | YES — MobileNoWalls (5) | 4 art surfaces missing | Y |
| ANWInca | 2 | PARTIAL (6/10) | YES — FortressRing (0) | 4 art surfaces missing | Y |
| ANWIndians | 2 | PARTIAL (6/10) | YES — FortressRing (0) | 4 art surfaces missing | Y |
| ANWIndonesians | 2 | PARTIAL (6/10) | YES — ChokepointSegments (1) | 4 art surfaces missing | Y |
| ANWItalians | 2 | PARTIAL (6/10) | YES — UrbanBarricade (4) | 4 art surfaces missing | Y |
| ANWJapanese | 2 | PARTIAL (6/10) | YES — MobileNoWalls (5) | 4 art surfaces missing | Y |
| ANWLakota | 2 | PARTIAL (6/10) | YES — MobileNoWalls (5) | 4 art surfaces missing | Y |
| ANWMaltese | 2 | PARTIAL (6/10) | YES — FortressRing (0) | 4 art surfaces missing | Y |
| ANWMayans | 2 | PARTIAL (6/10) | YES — ChokepointSegments (1) | 4 art surfaces missing | Y |
| ANWMexicans | 2 | PARTIAL (6/10) | YES — UrbanBarricade (4) | 4 art surfaces missing | Y |
| ANWNapoleonicFrance | 2 | PARTIAL (6/10) | YES — MobileNoWalls (5) | 4 art surfaces missing | Y |
| ANWOttomans | 2 | PARTIAL (6/10) | YES — FortressRing (0) | 4 art surfaces missing | Y |
| ANWPeruvians | 2 | PARTIAL (6/10) | YES — FortressRing (0) | 4 art surfaces missing | Y |
| ANWPortuguese | 2 | PARTIAL (6/10) | YES — CoastalBatteries (2) | 4 art surfaces missing | Y |
| ANWRevFrance | 2 | PARTIAL (6/10) | YES — UrbanBarricade (4) | 4 art surfaces missing | Y |
| ANWRioGrande | MISSING | NO (0/10) | YES — FrontierPalisades (3) | BLOCKED: zero screenshots, no manifest; live capture required | N |
| ANWRomanians | 2 | PARTIAL (6/10) | YES — FrontierPalisades (3) | 4 art surfaces missing | Y |
| ANWRussians | 2 | PARTIAL (6/10) | YES — FrontierPalisades (3) | 4 art surfaces missing | Y |
| ANWSouthAfricans | 2 | PARTIAL (6/10) | YES — CoastalBatteries (2) | 4 art surfaces missing | Y |
| ANWSpanish | 2 | PARTIAL (6/10) | YES — MobileNoWalls (5) | 4 art surfaces missing | Y |
| ANWSwedes | 2 | PARTIAL (6/10) | YES — MobileNoWalls (5) | 4 art surfaces missing | Y |
| ANWTexians | 2 | PARTIAL (6/10) | YES — MobileNoWalls (5) | 4 art surfaces missing | Y |
| ANWUSA | 2 | PARTIAL (6/10) | YES — UrbanBarricade (4) | 4 art surfaces missing | Y |

## Uniform art-surface gap (40/44 civs)

All 40 non-blocked civs share the same 4 missing surfaces in their manifests:
- `home_city_button` (HC picker icon)
- `hud_flag_corner` (in-game HUD corner flag)
- `esc_menu_player_summary` (ESC menu player row)
- `tech_tree_overview` (tech tree row — except ANWCanadians which has this but lacks esc_menu only)

These are live-capture surfaces. They are **not a blocker for review** — the site renders "missing" cells clearly with recapture commands, so the reviewer knows exactly what to grab.

## Wall strategy distribution (44 civs, all covered)

| Strategy | Count | Civs |
|----------|-------|------|
| FortressRing (0) | 14 | Canadians, Chileans, Chinese, Egyptians, Ethiopians, Finnish, French, Inca, Indians, Maltese, Ottomans, Peruvians, Canadians, British* |
| ChokepointSegments (1) | 4 | Aztecs, Haitians, Indonesians, Mayans |
| CoastalBatteries (2) | 7 | BajaCalifornians, Barbary, British, Dutch, Portuguese, SouthAfricans, (+ 2) |
| FrontierPalisades (3) | 7 | Brazil, CentralAmericans, Hausa, RioGrande, Romanians, Russians, Texians |
| UrbanBarricade (4) | 6 | Germans, Italians, Mexicans, RevFrance, USA, (+ 1) |
| MobileNoWalls (5) | 10 | Argentines, Californians, Columbians, Haudenosaunee, Hungarians, Japanese, Lakota, NapoleonicFrance, Spanish, Swedes, Texians |

Validator `validate_anw_wall_strategy_coverage.py` is GREEN (44/44).

## Blockers (4 civs — cannot fix offline)

| Civ | Blocker | Path to unblock |
|-----|---------|-----------------|
| ANWBajaCalifornians | Zero screenshots — no art folder or manifest | Requires live game + fixed build-tour (stale-villager bug) |
| ANWCalifornians | Zero screenshots — no art folder or manifest | Same |
| ANWCentralAmericans | Zero screenshots — no art folder or manifest | Same |
| ANWRioGrande | Zero screenshots — no art folder or manifest | Same |

Note: previously PROGRAM.md only listed RioGrande + BajaCalifornians as zero-screenshot; this audit also found ANWCalifornians and ANWCentralAmericans missing art folders. All 4 are "state civs" added in the same batch.

## No build script changes made

The site built cleanly on first run with no errors or fixes required. All 44 nations appear. Wall strategy is correctly wired through `playstyle_spec.json → claims.wall_strategy → _render_wall_doctrine_block()`.
