# Verified In-Game UI Coordinates (Confirmed via ANWBritish capture session 2026-05-20)

All coordinates are at game resolution **1920x1080** in the gamescope nested
Xwayland window. Use `xdotool --window $WID` (no global cursor grab).

## HUD top-right icons (constant Y=35)
| Icon         | x    | y  | Notes                                        |
|--------------|------|----|----------------------------------------------|
| Map/objectives | 1640 | 35 | Book + map landscape                       |
| **Diplomacy**  | **1691** | **35** | Inkwell + red quill — opens PLAYER SUMMARY |
| Trumpet (tasks)| 1750 | 35 | Golden horn                               |
| **Gears (ESC menu)** | **1860** | **30** | Two interlocked gears — opens game menu |

F-keys / hotkeys that do NOT work in this build:
- F3, F4 → diplomacy panel (use 1691,35 instead)
- Tab → no fullscreen scoreboard (built-in score panel is always top-right)
- Arrow keys → did not pan camera reliably with --window flag

## Diplomacy Panel — PLAYER SUMMARY layout
Opens via click at (1691, 35).

Panel ranges roughly x=350-1500, y=140-830.

### Player rows (y-coords, fixed 40px spacing)
| Player | y   |
|--------|-----|
| P1 (self) | 385 |
| P2     | 425 |
| P3     | 465 |
| P4     | 505 |
| P5     | 545 |
| P6     | 585 |
| **P7** | **625** |
| P8     | 665 |

### Player flag click area (clicking opens that player's home city + deck)
- **VERIFIED 2026-06-01**: The clickable area that opens the AI Home City is the
  **player name text**, NOT the small flag icon. Use x ≈ 500 (not 380).
- Click `(500, row_y)` to open AI Home City view from diplomacy.
- Flag x=380 is documented as the flag icon location but does NOT trigger HC navigation.
- This is the **only** way found to see an AI's home city + deck for visual confirmation.

### Stance radio columns (per row)
| Column   | x    |
|----------|------|
| ALLY     | 970  |
| NEUTRAL  | 1080 |
| ENEMY    | 1190 |

Click pattern to ally with P7: `click(970, 625)` then `click(510, 815)` (APPLY).

### Bottom buttons (y ≈ 815)
| Button | x center |
|--------|---------|
| APPLY  | 510 |
| CLEAR TRIBUTES | 960 |
| CLOSE  | 1410 |

## ESC Menu (opened via gears at 1860,30) — menu items at x=1830
| Item       | y   |
|------------|-----|
| Photo Mode | 90  |
| Tech Tree  | 140 |
| Save       | 185 |
| Load       | 230 |
| Restart    | 275 |
| Options    | 320 |
| **Resign** | **365** |
| Quit       | 410 |

## Resign Confirmation Dialog (after clicking Resign)
| Button | Center |
|--------|--------|
| YES    | (760, 605) |
| NO     | (1080, 605) |

## Post-Resign "You Abandon Your Town" dialog
| Button | Center |
|--------|--------|
| VIEW MAP      | (810, 737)  |
| VIEW POSTGAME | (1145, 737) |

## Postgame Results Screen tabs (top, y ≈ 55)
| Tab           | x   |
|---------------|-----|
| AWARDS        | 175 |
| RESOURCES     | 360 |
| ECONOMY       | 545 |
| MILITARY      | 735 |
| EXPERIENCE    | 935 |
| TIMELINE      | 1130 |
| GAME SUMMARY  | 1340 |

## Minimap (bottom-right circle)
- Bounding box: (1620, 850) to (1900, 1075)
- Click on minimap to jump camera to that map position.
- Player base detection: sample minimap region, find dominant colored clusters.
- Verified player color sampling at score panel x=1660:
  | P# | RGB                       | Color |
  |----|---------------------------|-------|
  | P1 | (26,19,154)               | BLUE  |
  | P2 | (189,41,32)               | RED   |
  | P3 | (168,164,15)              | YELLOW |
  | P4 | (128,10,78)               | PURPLE |
  | P5 | (43,125,32)               | GREEN |
  | P6 | (179,117,18)              | ORANGE |
  | **P7** | **(37,168,161)**     | **TEAL**  |
  | P8 | (180,84,118)              | PINK  |
- Score panel rows for each player: y ≈ 50 + (player_index)*40 at x=1660.

## In-game cheats verified working (Enter to open chat, type, Enter to send)
| Cheat code | Effect | Verified |
|------------|--------|----------|
| `X marks the spot` | Reveal full map (incl. minimap) | ✅ |
| `marco` (AoE2 cheat) | NOT recognized in AoE3 DE | ❌ |
| `give me liberty or give me coin` | +10000 gold | unverified visually |
| `speed always wins` | Faster building/training | unverified visually |

## Surfaces captured for ANWBritish (template — apply to other 45 civs)
1. `lobby_portrait` — picker selection (in lobby)
2. `loading_flag` — loading screen banner
3. `home_city_button` — HUD home city button bottom-left
4. `hud_flag_corner` — player's flag corner of HUD
5. `home_city_scene` — Click HC button → London scene with **A NEW WORLD** deck name
6. `tech_tree_overview` — ESC → Tech Tree → custom **British Empire (Tudor)** lore reads
7. `diplomacy_panel` — click 1691,35 → PLAYER SUMMARY with all 8 players
8. `diplomacy_ally_portrait` — set ally + APPLY → notification "X has changed their diplomatic stance towards you to Ally"
9. `ai_home_city_scene` + `ai_deck_view` — click flag at (380, row_y) in diplomacy → AI's HC opens (deck name displays as "HIDDEN" — that's a game feature for AI decks, NOT a bug)
10. `scoreboard_player_row` — always-visible top-right score panel (no Tab needed)
11. `wall_playstyle_visual` — `X marks the spot` + minimap nav to AI base (use player color to find on minimap)
12. `endgame_flag` — Resign → VIEW POSTGAME → all 8 player flags + final scores

## HC Panel Close Button (verified 2026-06-01)
The Home City (HC) panel opened via the HC button (bottom-left HUD) has a close button **X**
at **(1870, 865)**. Clicking it closes the HC panel and returns to the in-game map/scoreboard view.
This is distinct from ESC (which opens the ESC menu) or clicking elsewhere.

## Civ Picker Index Correction (verified 2026-06-01)
The `ANW_TO_PICKER_INDEX['ANWBritish'] = 7` mapping is INCORRECT for the current picker list.
Actual picker list (from visual inspection 2026-06-01):
  - Down×0 = Random Personality
  - Down×1 = Argentine Confederation (Buenos Aires)
  - Down×2 = Bourbon France (Paris)
  - Down×3 = British Empire (London)  ← CORRECT index for British
  - Down×4 = Cruzor Maya (Chan Santa Cruz)
  - Down×5 = Dutch Republic (Amsterdam)
  - Down×6 = Empire of Brazil (Rio de Janeiro)
  - Down×7 = Ethiopian Empire (Gondar)  ← WRONG index (previously mapped for British)
Use Down×3 (not Down×7) to select British Empire in the civ picker.

## AGE-UP BLOCKERS (confirmed 2026-06-01)
- `H` hotkey: opens Home City panel, does NOT select the Town Center.
- `AGE_UP_BTN = (1356, 1029)` is UNVALIDATED: zero gold pixels found at this location
  even after navigating to player base area. The actual age-up button location has not
  been empirically confirmed.
- Automated age-up via `anw_autonomous_age_up_runner.py` fails because both the H-select
  and the pixel probe are unreliable.
- Manual TC selection requires clicking directly on the TC building in the game world.
- On Budapest 8-player map, Team 1 ally buildings (Napoleon, Mannerheim, etc.) are
  interleaved with the British player's buildings; visual identification of own TC required.

## CRITICAL: Diplomacy click opens AI HC — discovered behavior
User asked: "click on the diplomacy ai flag to break up their homecity".
ANSWER: Click the player **name text** at `(500, row_y)` in the open diplomacy panel.
NOTE: x=380 (flag icon) does NOT work — tested 2026-06-01, clicks did not trigger HC.
x=500 (player name area) confirmed working 2026-06-01.
This opens that AI's Home City view, showing their deck (name displays
as "HIDDEN" because AI decks are private by design) and their leader
portrait. Player communication portrait visible at bottom-right.
