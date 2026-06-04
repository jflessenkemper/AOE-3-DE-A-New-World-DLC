# Live Template Capture — Status (2026-04-28)

_Captured against `Age of Empires III: Definitive Edition v100.15.59076.0 P2`, mod `A New World AI` enabled, gamescope `1920×1080@60`, English locale._

## What worked

- AoE3 launched cleanly under gamescope (PID-tree includes `gamescope -W 1920 -H 1080 -r 60 → reaper → Proton → AoE3DE_s.exe`). The embedded Xwayland is on `:1`, gamescope wayland socket at `/run/user/1000/gamescope-0`.
- **Screen capture works** via `gamescopectl screenshot <abs-path>` — produces a real 1920×1080 PNG of the actual game framebuffer (≈4.5 MB sRGB).
  - `grim` does NOT work (gamescope doesn't expose the wlr-screencopy protocol).
  - `import -display :1 -window root` returns an all-black 1×1-pixel canvas (gamescope's Xwayland is rootless and doesn't backref the rendered framebuffer).
- **Mouse + keyboard input works** via `xdotool` against `DISPLAY=:1`. Verified: keyboard (`Down × N + Return` navigates main menu) and mouse (`mousemove → click 1` reached and opened the team-color dropdown).
- **OCR is unreliable** on this UI font (Trajan-style caps on textured wood). Tesseract reads almost nothing on the main menu and lobby even with thresholding/inversion — only single tokens like `HOME` matched. **Plan: rely on coord-based clicks + image templates rather than `click_text` for menu navigation.** OCR may still work for the larger result-screen text (`Victory`/`Defeat`).

## Captured raw screenshots

`_raw/01_main_menu.png` — 1920×1080, full main menu
`_raw/05_skirmish_lobby.png` — 1920×1080, Single Player Skirmish lobby (default 8-player Free For All, Great Lakes, Supremacy, Hard, Fast)

## Cropped templates (verified)

| Template | Source | Crop | Verified |
|----------|--------|------|----------|
| `skirmish_button.png` | 01_main_menu | 200×55 + 30,460 | ✅ shows "SKIRMISH" |
| `continue_button.png` | 01_main_menu | 200×55 + 30,200 | ✅ shows "CONTINUE" |
| `start_game_button.png` | 05_skirmish_lobby | 400×70 + 1480,1000 | ✅ shows "PLAY" |

## Confirmed click coordinates (1920×1080 lobby and main menu)

All coords are now in **`tools/aoe3_automation/lobby_coords.json`** and
driven by **`tools/aoe3_automation/lobby_driver.py`**. Verified end-to-end
2026-04-28 by `--select-civ aztecs` selecting Aztec Empire and the P1 slot
showing the Aztec portrait.

| Element | (x, y) center | How verified |
|---------|---------------|--------------|
| Main menu → Skirmish item | `(130, 488)` | mouse click → lobby opened |
| Lobby → Player 1 civ "?" picker | `(630, 170)` | click → 2.06M-pixel diff vs clean = picker open ✅ |
| Lobby → Player 1 team color dropdown | `(1015, 170)` | yellow-pixel scan; click opens color picker |
| Lobby → Map (Great Lakes) | `(1645, 430)` | click → fullscreen Select Map dialog opens ✅ |
| Lobby → Difficulty (Hard) | `(1645, 729)` | click → dropdown opens with Easy/Std/Mod/Hard/Hardest/Extreme ✅ |
| Lobby → Game Speed (Fast) | `(1645, 825)` | click → popup opens with Slow/Medium/Fast (no Fastest) ✅ |
| Lobby → PLAY button | `(1700, 1029)` | template-cropped, coord-confirmed |
| Civ picker → row N | `(440, 316 + 64·N)` | click row 3 (y=508) → Aztec selected ✅ |
| Civ picker → OK | `(215, 962)` | bright-pixel scan + empirical click confirms |
| Civ picker → Deck Builder | `(425, 962)` | bright-pixel scan |
| Civ picker → Cancel | `(645, 962)` | click → returns to clean lobby with no change ✅ |
| Map dialog → Cancel | `(1340, 990)` | click → returns to clean lobby ✅ |
| Lobby → Back (top-left) | `Escape` key works (returns to main menu) |

## Civ picker mechanics

- Opens by clicking the `?` icon (or anywhere in the civ slot box) at
  P1 row.
- Shows 10 civs at a time, alphabetical, with "Random Personality" at
  the very top.
- **Mouse scroll-wheel down** scrolls the list **one row per click**
  (anchor at any y inside the picker). Letter-jump (typing 'z') and
  arrow-key navigation **do not** move the highlight.
- Mouse hover sets the highlight; clicking a row selects it. OK button
  confirms; Cancel discards.
- **Escape does NOT close the picker** — must use Cancel button.

## Game Speed dropdown

- Has only **3 options** in this build: Slow / Medium / Fast.
- "Fast" IS the maximum (no Fastest exists), so the matrix needs no
  change from the lobby default.

## Defaults that match matrix needs

The fresh Skirmish lobby already has:

- 8 players, Free For All, P1 = Flessenkemper / `?` civ
- Map: Great Lakes
- Game Mode: Supremacy
- Game Rules: Standard
- Starting Age: Nomad, Ending Age: Imperial Age
- Difficulty: **Hard** ✅
- Starting Resources: Standard
- Game Speed: **Fast** ✅ (= max)

So for the matrix flow, the only required action per iteration is:
**open civ picker → select target civ → OK → click PLAY → wait for
Victory/Defeat → continue → reset to Random → repeat**.

## Coordinates that need empirical confirmation

These were inferred but not verified to trigger their UI:

- Lobby → Player 1 civ "?" dropdown — likely between `x=860` and `x=1000` at `y≈140-200`, but pixel-sweep showed only wood-colored RGB everywhere in that range. The `?` placeholder appears to be drawn in the same dark-wood tone as the background; the clickable area location is not yet pinned.
- Game Speed dropdown (right column, near bottom)
- Game Rules dropdown
- Difficulty dropdown
- Map select (Great Lakes)
- Advanced Settings — **probably not a separate panel in AoE3 DE**. Settings like Reveal Map / Game Speed / Handicap are individual dropdowns/toggles in the right column of the lobby (no nested "Advanced" panel).

## Templates still missing

From the original 10-template list in `HARNESS_EXTENSIONS.md`:

1. ~~`single_player_button.png`~~ — **not needed**: AoE3 DE main menu shows Skirmish directly.
2. `skirmish_button.png` ✅
3. `dismiss_update.png` — optional; not seen in this session.
4. `player1_civ_dropdown.png` — **needed but coords unconfirmed**.
5. `leader_dropdown.png` — **needs investigation**: AoE3 DE may put leader inside the civ-picker rather than a separate dropdown. Open civ "?" first to see.
6. ~~`advanced_settings_button.png`~~ — likely not applicable; settings are inline.
7. `game_speed_fastest.png` — needs Game Speed dropdown opened to capture.
8. `reveal_map_on.png` — needs the Game Rules / settings dropdown opened.
9. ~~`advanced_settings_close.png`~~ — likely not applicable.
10. `start_game_button.png` ✅

## Recommended next steps (10-minute manual session at the rig)

With the game already at the lobby, do one Skirmish-prep walk and run `gamescopectl screenshot <path>` at each state. The expensive part (figuring out gamescope, X displays, screenshot mechanism) is solved; this is now point-and-shoot.

1. Click the P1 civ "?" — write down the cursor's last position (xdotool getmouselocation reports it). Capture the open civ-picker.
2. Pick any civ (e.g. British). Capture the lobby with civ filled in.
3. If a leader-portrait dropdown appears next to the civ box: capture it.
4. Open Game Speed dropdown → capture → crop the "Fastest" entry into `game_speed_fastest.png`.
5. Open the "Game Rules" dropdown (currently "Standard") → look for `Reveal Map` toggle → capture → crop.
6. Save raw PNGs to `_raw/` named `11_civ_picker_open.png`, `12_with_civ.png`, `13_speed_open.png`, `14_rules_open.png`.

Then re-run `python3 tools/aoe3_automation/flows/matrix_run_all.py --dry-run` and the existing flow JSON should template-match against the captured chrome.

## Alternative flow without full template set

If template capture remains awkward, the matrix flow can be rewritten to use direct coord clicks:

```json
{ "action": "click", "x": 130, "y": 488 }      // → enter Skirmish lobby
{ "action": "click", "x": 920, "y": 145 }      // → open P1 civ dropdown (needs confirmed coord)
{ "action": "click_text", "texts": ["${CIV_NAME}"] }  // pick civ from open list (OCR may struggle on civ names; backup: arrow-key nav)
{ "action": "click", "x": 1700, "y": 1030 }    // → PLAY
{ "action": "wait_text", "texts": ["Victory","Defeat"], "timeout": 3600 }
```

`click_text` will work for **larger result-screen text** (Victory/Defeat) but is unreliable on the lobby's small Trajan caps. If we can pin the civ-list y-coords once (each list entry sits at a fixed pixel offset relative to the dropdown header), we can drop OCR entirely and pick by `(x, y_header + civ_index × row_height)`.
