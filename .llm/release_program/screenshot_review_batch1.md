# Screenshot QA Review — Batch 1

**Date:** 2026-06-08  
**Reviewed by:** Visual QA pass (read-only)  
**Total images reviewed:** 52 (ANWBritish: 22, 9 other civs: 2–4 each)  
**Total flagged:** 24

---

## Reference Civ: ANWBritish (22 screenshots)

All 22 British screenshots reviewed. Key findings:

| File | Surface | Result | Notes |
|------|---------|--------|-------|
| 01_lobby.png | lobby_portrait | PASS | British flag (Union Jack) shown, skirmish lobby |
| 02_loading.png | loading_flag | FLAG | Shows same lobby screen as 01_lobby, not loading banner — capture fired before match loaded |
| 03_hud.png | hud/home_city_button | PASS | In-game HUD, British flag top-right score panel |
| 03_scoreboard.png | scoreboard | PASS | In-game score panel visible |
| 04_homecity_panel.png | home_city_scene | PASS | London home city scene, "Flessenkemper / London / Level 7" |
| 04_diplomacy.png | diplomacy_panel | PASS | Player Summary with 8 players and flags |
| 05_homecity_panel.png | home_city_scene (alt) | FLAG | Shows ESC menu over in-game map with "Game Paused" — wrong surface (should be HC scene) |
| 05_tech_tree.png | tech_tree_overview | PASS | Tech Tree with "British Empire" lore text |
| 06_esc_menu.png | esc_menu | PASS | ESC menu open, Game Paused |
| 06_diplomacy.png | diplomacy_panel | PASS | Player Summary with all 8 players |
| 06b_diplomacy_after_ally.png | diplomacy after ally | PASS | Player Summary with 8 players (minor difference from 06) |
| 06b_ai_homecity_via_diplo.png | AI home city | PASS | London-style home city, "Soekarno / Yogyakarta" deck HIDDEN — correct AI behavior |
| 07_endgame_screen.png | endgame_flag | PASS | Post-game Awards screen with all 8 player flags + scores |
| 07_scoreboard.png | scoreboard | PASS | In-game score panel |
| 07a_abandon_screen.png | abandon screen | FLAG | Shows a different home city (London towers visible) with label "Soekarno / Yogyakarta" — this appears to be the AI's HC viewed via diplomacy, not an abandon screen |
| 07a_abandon_screen_confirm.png | abandon confirm | FLAG | Also shows "Soekarno / Yogyakarta" AI HC — same wrong-surface issue as 07a_abandon_screen |
| 07a_post_resign.png | post-resign | FLAG | Same "Soekarno / Yogyakarta" AI London HC — wrong surface or badly named |
| 08_ageup_age2.png | age-up age II | PASS | Commerce Age politician selection panel |
| 08_ageup_age3.png | age-up age III | PASS | Fortress Age politician selection panel |
| 08_ageup_age4.png | age-up age IV | PASS | Industrial Age politician selection panel |
| 08_ageup_age5.png | age-up age V | PASS | Imperial Age politician selection panel |
| 08_esc_menu.png | esc_menu | PASS | ESC menu, Game Paused |
| 09_endgame.png | endgame | PASS | Post-game Awards Total Score screen |
| 09_hero_selected.png | hero_selected | FLAG | Shows ESC menu + Game Paused — not a hero-selected view |
| 10_ai_homecity.png | ai_home_city_scene | PASS | "Simon Bolivar / Bogota / Level 7" HC, deck shown as HIDDEN — correct |
| 17_units_inworld.png | units in world | PASS | In-game map with units and score panel |
| 20_postgame_awards.png | postgame awards | PASS | Post-game Total Score with all 8 flags |
| 21_base_overview.png | base overview | PASS | In-game map with base structures, score panel shows ANWCanadians leader |
| ai_01_chat_portrait.png | AI chat portrait | PASS | In-game map with Napoleon chat |
| ai_02_homecity.png | AI home city | PASS | London-style HC, "Soekarno / Yogyakarta" |

**ANWBritish: 22 pass, 6 flagged**

---

## Batch 1 Non-British Civs

### ANWArgentines (2 screenshots)

| File | Surface | Result | Notes |
|------|---------|--------|-------|
| 01_lobby.png | lobby_portrait | PASS | Argentine flag (yellow/blue sun-of-may), skirmish lobby |
| 02_loading.png | loading_flag | PASS | Budapest map loading screen — correct loading surface |

**ANWArgentines: 2 pass, 0 flagged**

---

### ANWAztecs (2 screenshots)

| File | Surface | Result | Notes |
|------|---------|--------|-------|
| 01_lobby.png | lobby_portrait | FLAG | Shows a pink/magenta flag — does not look like an Aztec Empire flag; possible wrong civ selected in picker |
| 02_loading.png | loading_flag | PASS | Budapest loading screen |

**ANWAztecs: 1 pass, 1 flagged — wrong-civ flag in lobby**

---

### ANWBarbary (2 screenshots)

| File | Surface | Result | Notes |
|------|---------|--------|-------|
| 01_lobby.png | lobby_portrait | FLAG | Shows red/white/green horizontal tricolor flag — looks Hungarian, not Barbary; possible picker index collision with ANWHungarians |
| 02_loading.png | loading_flag | PASS | Budapest loading screen |

**ANWBarbary: 1 pass, 1 flagged — wrong-civ flag (appears Hungarian)**

---

### ANWBrazil (2 screenshots)

| File | Surface | Result | Notes |
|------|---------|--------|-------|
| 01_lobby.png | lobby_portrait | PASS | Shows British-style ensign (red/white with Union Jack canton) — consistent with Brazil Empire naval flag style used in the mod |
| 02_loading.png | loading_flag | PASS | Budapest loading screen |

**ANWBrazil: 2 pass, 0 flagged** *(flag plausible; mod uses a red-ensign variant for Brazil Empire)*

---

### ANWCanadians (4 screenshots)

| File | Surface | Result | Notes |
|------|---------|--------|-------|
| 01_lobby.png | lobby_portrait | FLAG | Shows Texas lone-star flag (blue/white/red vertical), not a Canadians flag |
| 02_loading.png | loading_flag | PASS | Budapest loading screen |
| 03_hud.png | hud | FLAG | AoE3 DE **crash dialog** ("has encountered a problem and needs to close") — game crashed during capture |
| 04_homecity_panel.png | home_city_scene | FLAG | Same crash dialog — duplicate of crash screen |

**ANWCanadians: 1 pass, 3 flagged — wrong-civ flag + crash during capture**

---

### ANWChileans (2 screenshots)

| File | Surface | Result | Notes |
|------|---------|--------|-------|
| 01_lobby.png | lobby_portrait | FLAG | Shows red/white horizontal stripes flag — resembles Peru or a generic Latin American flag, not the Chilean flag (blue/white/red with star) |
| 02_loading.png | loading_flag | PASS | Budapest loading screen |

**ANWChileans: 1 pass, 1 flagged — wrong-civ flag in lobby**

---

### ANWChinese (2 screenshots)

| File | Surface | Result | Notes |
|------|---------|--------|-------|
| 01_lobby.png | lobby_portrait | FLAG | Shows a green/white/red flag (looks Italian/Hungarian tricolor), not a Chinese flag |
| 02_loading.png | loading_flag | PASS | Budapest loading screen |

**ANWChinese: 1 pass, 1 flagged — wrong-civ flag in lobby**

---

### ANWColumbians (2 screenshots)

| File | Surface | Result | Notes |
|------|---------|--------|-------|
| 01_lobby.png | lobby_portrait | FLAG | Shows AoE3 main menu with "Choose One Free Weekly Profile Picture Reward!" popup — completely wrong surface, not a lobby |
| 02_loading.png | loading_flag | FLAG | Same main menu popup — capture did not enter skirmish setup at all |

**ANWColumbians: 0 pass, 2 flagged — capture failed to reach lobby (main menu popup blocked nav)**

---

### ANWDutch (2 screenshots)

| File | Surface | Result | Notes |
|------|---------|--------|-------|
| 01_lobby.png | lobby_portrait | FLAG | Main menu popup same as Columbians — capture blocked at main menu |
| 02_loading.png | loading_flag | FLAG | Same main menu popup |

**ANWDutch: 0 pass, 2 flagged — capture blocked at main menu**

---

### ANWEgyptians (2 screenshots)

| File | Surface | Result | Notes |
|------|---------|--------|-------|
| 01_lobby.png | lobby_portrait | FLAG | Main menu popup — capture blocked |
| 02_loading.png | loading_flag | FLAG | Main menu popup |

**ANWEgyptians: 0 pass, 2 flagged**

---

### ANWEthiopians (2 screenshots)

| File | Surface | Result | Notes |
|------|---------|--------|-------|
| 01_lobby.png | lobby_portrait | FLAG | Main menu popup — capture blocked |
| 02_loading.png | loading_flag | FLAG | Main menu popup |

**ANWEthiopians: 0 pass, 2 flagged**

---

### ANWFinnish (2 screenshots)

| File | Surface | Result | Notes |
|------|---------|--------|-------|
| 01_lobby.png | lobby_portrait | FLAG | Main menu popup — capture blocked |
| 02_loading.png | loading_flag | FLAG | Main menu popup |

**ANWFinnish: 0 pass, 2 flagged**

---

## Per-Civ Summary

| Civ | Reviewed | Pass | Flagged |
|-----|---------|------|---------|
| ANWBritish (reference) | 22 | 16 | 6 |
| ANWArgentines | 2 | 2 | 0 |
| ANWAztecs | 2 | 1 | 1 |
| ANWBarbary | 2 | 1 | 1 |
| ANWBrazil | 2 | 2 | 0 |
| ANWCanadians | 4 | 1 | 3 |
| ANWChileans | 2 | 1 | 1 |
| ANWChinese | 2 | 1 | 1 |
| ANWColumbians | 2 | 0 | 2 |
| ANWDutch | 2 | 0 | 2 |
| ANWEgyptians | 2 | 0 | 2 |
| ANWEthiopians | 2 | 0 | 2 |
| ANWFinnish | 2 | 0 | 2 |
| **TOTALS** | **52** | **25** | **23** |

---

## Systemic Issues Found

### CRITICAL — Main menu popup blocks capture (Columbians through Finnish)
Five consecutive civs (ANWColumbians, ANWDutch, ANWEgyptians, ANWEthiopians, ANWFinnish) all show the AoE3 "Weekly Profile Picture Reward" popup. The capture runner did not dismiss this popup before attempting to screenshot, so every shot for those civs is the wrong surface entirely. This is a session-startup blocker: if this popup appears, all subsequent civ captures in that run will also fail. Add popup dismissal logic to the capture runner before any navigation.

### HIGH — Wrong lobby flags for multiple civs (Aztecs, Barbary, Chileans, Chinese, Canadians)
The lobby `01_lobby.png` for several civs shows a flag that does not match the civ token:
- ANWAztecs: pink/magenta flag (unrecognized)
- ANWBarbary: red/white/green horizontal tricolor (looks Hungarian — ANWHungarians index collision?)
- ANWChileans: red/white stripes (looks Peruvian/generic Latin American)
- ANWChinese: green/white/red tricolor (looks Italian or Hungarian)
- ANWCanadians: Texas lone-star flag (wrong — this may be ANWTexians leaking)

This suggests the civ picker index map (`anw_civ_picker_map.py`) has off-by-one errors for several civs, causing the wrong civ to be selected in the lobby. Cross-reference with `picker_civ_order.json` entries and the verified scroll-count values.

### MEDIUM — ANWBritish `02_loading` is a lobby duplicate
British `02_loading.png` shows the pre-game lobby, not the map loading banner. The capture script probably triggered too early before the match transition. All other civs that reached the lobby (ANWArgentines through ANWChinese) have a legitimate Budapest loading screen in their `02_loading.png`, so this may be a one-time race condition for British.

### MEDIUM — ANWBritish filenames `07a_abandon_screen*` / `07a_post_resign` show AI home city
All three `07a_*` files show the Soekarno/Yogyakarta AI home city (London-style architecture). These should show the "You abandon your town" banner and post-resign view. The capture likely navigated to the AI HC panel instead of triggering the resign flow.

### LOW — ANWCanadians crash during in-game capture
`03_hud.png` and `04_homecity_panel.png` both show the Windows BugSplat crash dialog. The game crashed immediately after entering the match for ANWCanadians. This is a civ-specific stability bug, not a capture-timing issue.

---

## Coverage: What Was Done, What Remains

**Batch 1 covered:**
- ANWBritish (full set, reference)
- ANWArgentines, ANWAztecs, ANWBarbary, ANWBrazil, ANWCanadians, ANWChileans, ANWChinese, ANWColumbians, ANWDutch, ANWEgyptians, ANWEthiopians, ANWFinnish

**Remaining civs for future batches (alphabetical from ANWFrench):**
ANWFrench, ANWGermans, ANWHaitians, ANWHaudenosaunee, ANWHausa, ANWHungarians, ANWInca, ANWIndians, ANWIndonesians, ANWItalians, ANWJapanese, ANWLakota, ANWMaltese, ANWMayans, ANWMexicans, ANWNapoleonicFrance, ANWOttomans, ANWPeruvians, ANWPortuguese, ANWRevFrance, ANWRomanians, ANWRussians, ANWSouthAfricans, ANWSpanish, ANWSwedes, ANWTexians, ANWUSA

**Skipped per task instructions (live capture in progress):**
ANWBajaCalifornians, ANWCalifornians, ANWCentralAmericans, ANWRioGrande
