# UI Surface Map

> Canonical reference for every in-game UI surface used by the ANW visual-capture pipeline.
> All coordinates are verified at **1920x1080** via the gamescope nested Xwayland window
> (`xdotool --window $WID`; no global cursor grab).
>
> Source of truth: [`tools/aoe3_automation/verified_coords_british.md`](../../tools/aoe3_automation/verified_coords_british.md)
> (confirmed via ANWBritish capture session 2026-05-20 / 2026-06-01).

---

## HUD top-right icons (constant Y=35)

These icons are always visible during an in-game skirmish.

| Icon | Click target | Notes |
|------|-------------|-------|
| Map / objectives | (1640, 35) | Book + map landscape icon |
| **Diplomacy** | **(1691, 35)** | Inkwell + red quill — opens PLAYER SUMMARY panel |
| Trumpet (tasks) | (1750, 35) | Golden horn icon |
| **Gears (ESC menu)** | **(1860, 30)** | Two interlocked gears — opens game menu |

### Known-broken keyboard inputs

| Input | Expected behavior | Actual result |
|-------|------------------|---------------|
| F3, F4 | Open diplomacy panel | Do NOT work — use (1691, 35) click instead |
| Tab | Open fullscreen scoreboard | No fullscreen scoreboard; use always-visible top-right score panel |
| Arrow keys | Pan camera | Unreliable with `--window` flag |

---

## Diplomacy Panel — PLAYER SUMMARY

Opened by clicking at **(1691, 35)**. Panel occupies roughly x=350–1500, y=140–830.

### Player rows (y-coords, fixed 40 px spacing)

| Player | y |
|--------|---|
| P1 (self) | 385 |
| P2 | 425 |
| P3 | 465 |
| P4 | 505 |
| P5 | 545 |
| P6 | 585 |
| P7 | 625 |
| P8 | 665 |

### Clickable areas per row

| Target | x | Note |
|--------|---|------|
| Player name text (opens AI Home City) | ~500 | **Verified 2026-06-01** — this is the only working trigger |
| Flag icon | ~380 | Documented location but does NOT trigger HC navigation |

Clicking the player name text opens that player's Home City + deck view. AI deck names display as "HIDDEN" — this is a game feature, not a bug.

### Stance radio columns

| Stance | x |
|--------|---|
| ALLY | 970 |
| NEUTRAL | 1080 |
| ENEMY | 1190 |

### Bottom buttons (y ≈ 815)

| Button | x center |
|--------|---------|
| APPLY | 510 |
| CLEAR TRIBUTES | 960 |
| CLOSE | 1410 |

To ally with P7: `click(970, 625)` then `click(510, 815)` (APPLY).

---

## ESC Menu

Opened via gears icon at **(1860, 30)**. Menu items at x=1830.

| Item | y |
|------|---|
| Photo Mode | 90 |
| Tech Tree | 140 |
| Save | 185 |
| Load | 230 |
| Restart | 275 |
| Options | 320 |
| **Resign** | **365** |
| Quit | 410 |

---

## Resign Confirmation Dialog

Appears after clicking Resign in the ESC menu.

| Button | Center |
|--------|--------|
| YES | (760, 605) |
| NO | (1080, 605) |

---

## "You Abandon Your Town" Dialog

Appears after confirming Resign.

| Button | Center |
|--------|--------|
| VIEW MAP | (810, 737) |
| **VIEW POSTGAME** | **(1145, 737)** |

---

## Postgame Results Screen

Tabs at the top of the postgame screen (y ≈ 55).

| Tab | x |
|-----|---|
| AWARDS | 175 |
| RESOURCES | 360 |
| ECONOMY | 545 |
| MILITARY | 735 |
| EXPERIENCE | 935 |
| TIMELINE | 1130 |
| GAME SUMMARY | 1340 |

---

## Minimap

Located bottom-right of the in-game HUD.

- Bounding box: (1620, 850) to (1900, 1075)
- Click to jump camera to that map position.
- Player color sampling at score panel x=1660:

| Player | RGB | Color |
|--------|-----|-------|
| P1 | (26, 19, 154) | BLUE |
| P2 | (189, 41, 32) | RED |
| P3 | (168, 164, 15) | YELLOW |
| P4 | (128, 10, 78) | PURPLE |
| P5 | (43, 125, 32) | GREEN |
| P6 | (179, 117, 18) | ORANGE |
| P7 | (37, 168, 161) | TEAL |
| P8 | (180, 84, 118) | PINK |

Score panel rows: y ≈ 50 + (player_index × 40) at x=1660.

---

## Home City (HC) Panel

Opened via the HC button (bottom-left HUD). Close button **X** at **(1870, 865)**.
Distinct from ESC (which opens the ESC menu).

---

## Civ Picker Dropdown Index

When selecting a civ via the AI opponent picker, the dropdown order is (verified 2026-06-01):

| Down presses | Entry |
|-------------|-------|
| 0 | Random Personality |
| 1 | Argentine Confederation (Buenos Aires) |
| 2 | Bourbon France (Paris) |
| 3 | British Empire (London) |
| 4 | Cruzor Maya (Chan Santa Cruz) |
| 5 | Dutch Republic (Amsterdam) |
| 6 | Empire of Brazil (Rio de Janeiro) |
| 7 | Ethiopian Empire (Gondar) |

> Note: `ANW_TO_PICKER_INDEX['ANWBritish'] = 7` is INCORRECT. Down×3 (not Down×7) selects British Empire.

---

## Canonical Capture Surfaces (per civ)

The 12 surfaces captured for ANWBritish serve as the template for all ~44 civs:

| # | Surface key | How to reach |
|---|-------------|-------------|
| 1 | `lobby_portrait` | Civ picker selection in lobby |
| 2 | `loading_flag` | Loading screen banner |
| 3 | `home_city_button` | HUD home city button (bottom-left) |
| 4 | `hud_flag_corner` | Player's flag corner of HUD |
| 5 | `home_city_scene` | Click HC button → home city scene with deck name |
| 6 | `tech_tree_overview` | ESC → Tech Tree |
| 7 | `diplomacy_panel` | Click (1691, 35) → PLAYER SUMMARY with all 8 players |
| 8 | `diplomacy_ally_portrait` | Set ally + APPLY → diplomatic stance notification |
| 9 | `ai_home_city_scene` + `ai_deck_view` | Click player name at (500, row_y) in diplomacy panel |
| 10 | `scoreboard_player_row` | Always-visible top-right score panel |
| 11 | `wall_playstyle_visual` | `X marks the spot` cheat + minimap nav to AI base |
| 12 | `endgame_flag` | Resign → VIEW POSTGAME → all 8 player flags + final scores |

---

## In-Game Cheats (verified working)

Activate via Enter → type → Enter:

| Cheat | Effect | Status |
|-------|--------|--------|
| `X marks the spot` | Reveal full map (including minimap) | Verified |
| `give me liberty or give me coin` | +10000 gold | Unverified visually |
| `speed always wins` | Faster building/training | Unverified visually |
| `marco` (AoE2) | Not recognized in AoE3 DE | Confirmed broken |

---

## Age-Up Blockers (confirmed 2026-06-01)

> ⚠ OPEN: Automated age-up is currently broken.

- `H` hotkey: opens Home City panel — does NOT select the Town Center.
- `AGE_UP_BTN = (1356, 1029)` is UNVALIDATED: zero gold pixels found at this location even after navigating to player base.
- `anw_autonomous_age_up_runner.py` fails because both H-select and pixel probe are unreliable.
- Manual TC selection requires clicking directly on the TC building in the game world.

---

## Cross-references

- [`tools/aoe3_automation/verified_coords_british.md`](../../tools/aoe3_automation/verified_coords_british.md) — primary source
- [`tools/validation/build_release_readiness_site.py`](../../tools/validation/build_release_readiness_site.py) — screenshot surface labels used in release site rendering
- [ANW capture ceiling](../../artifacts/validation/anw_site_text_art_audit.md) — known capture gaps
