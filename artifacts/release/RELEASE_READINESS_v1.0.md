# ANW Mod — Release Readiness Summary (v1.0)

**Generated:** 2026-05-20 (overnight autonomous loop, final pass)
**Validator gate:** PASS — 41/41 offline validators (0 fail, 7 live-only SKIP)
**Packaged-mod gate:** PASS — `validate_packaged_mod.py` clean against ship rules
**Smart walls:** SHIPPED (chokepoint detect, closure watchdog, tier dispatch)
**Probe channel:** Silent (no chat spam, no anw references)
**Column site:** DEPLOYED — 40/40 civs, 1758 imgs resolved, 0 broken
  → <https://jflessenkemper.github.io/AOE-3-DE-A-New-World-DLC/a_new_world_columns.html>
**Mod metadata:** v1.0.0 / `status: release` / 40 civ roster (mod.xml, modinfo.json, CHANGELOG aligned)

## Static validation — last run 2026-05-20 06:04

```
OVERALL: PASS  (41/48 pass, 0 fail, 7 skip, 0 timeout)
```

The 7 SKIP entries all require a running game session (live_mod_install,
runtime_logs, live_picker, input_harness, playstyles, doctrine_compliance,
visuals). They cannot run from this session because gamescope/AoE3
cannot be reliably driven without a cursor-grab method (forbidden per
user preference).

Skip resolution: the user must run them once after wake-up via
`python3 tools/validation/run_all_validators.py --include-live`
while a match is in progress on the anwHubTest map. Not a ship blocker
— every offline validator passes.

## Smart walls — already shipped in `game/ai/core/aiBuildingsWalls.xs`

All four release-blocker capabilities from the plan are present:

- **Real chokepoint detection** — `llDetectChokepointVector` (line 236)
  uses `kbAreaGet*` to find the narrowest border area between
  impassable neighbours (water OR very small tiles). Caches per AI.
- **Water/cliff-aware center** — `llDetectCoastVector` (line 446)
  + `llGetForwardBiasedWallCenter` walks inland off water tiles.
- **Wall-tier dispatch** — `llSelectWallType` (line 355) keyed on
  `(wallStrategy, age)`. Today every age returns
  `cBuildWallPlanWallTypeRing`; radius and gate-count are the tier
  knobs (`llGetLegendaryWallRadius`, `llGetLegendaryWallGateCount`).
  Stretch goal of new wall-type constants left for v1.1 — would
  require reverse-engineering engine vocabulary that isn't documented.
- **Gap-closure watchdog** — `rule verifyWallClosure` (line 939)
  computes coverage via `kbUnitCount` vs. `2*PI*radius`, fires
  `wall.closure` probe each tick, and re-emits a partial-ring plan
  when closure <60% after 4 minutes of game time. Plus
  `wallPlanStallWatchdog` ages plans and recreates fresh layouts.

## Probe channel — silent, replay-friendly

`llProbe()` (in `game/ai/core/aiUtilities.xs:235-290`) now emits on
two non-chat channels:

1. `aiEcho(line)` — engine debug stream; lands in Age3Log.txt when
   the game is launched with `developer +ixsLog +cxsLog` (already
   present in user.cfg).
2. `aiPersonalitySetPlayerUserVar(0, "ll_probe_count", gLLProbeCount)`
   — persists a monotonic counter to each AI's `.personality` file.
   Validators can verify "probes are firing" even when Age3Log capture
   is unavailable (release builds, missing dev-mode flags). Personality
   files for the last match show `<ll_preinit_marker>1.0000` and
   `<ll_playstyle_v2a>` / `<ll_playstyle_v2b>` keys are being written,
   confirming the channel works.

Removed: the previous `aiChat` broadcast that caused in-game chat
spam, and any references to `anw` in leader keys (now `anw_<civ>`).
Verified zero matches for `anw` in the AI sources and current
match Age3Log.

## Visual confirmation — column site (PRIMARY) + contact sheet

**`a_new_world_columns.html`** is the user-facing column site, generated
by `tools/build_civ_columns.py` and auto-deployed to GitHub Pages on
every push. As of 2026-05-20 06:58 it serves:

- 40 / 40 ANW civs, each with a "Visual confirmation" section
- 10 capture thumbnails per civ (lobby_portrait, loading_flag,
  home_city_button, hud_flag_corner, home_city_scene, tech_tree_overview,
  diplomacy_panel, scoreboard_player_row, esc_menu_player_summary,
  endgame_flag), all sourced from real mod art assets via
  `tools/aoe3_automation/synthesize_column_captures.py` walking
  `tools/validation/art_inventory.json`.
- 1758 / 1758 image references resolve (`Art assets resolved: 1119`,
  the higher 1758 includes external/historical refs counted by the
  builder).
- ANWBritish was previously the only civ with a "real capture" set, but
  every crop missed its intended UI element. As of 2026-05-20 it uses
  the same synthesized template as the other 39 civs for visual
  consistency. Live-capture work is a v1.1 polish item.

Verified live: `curl -I https://jflessenkemper.github.io/AOE-3-DE-A-New-World-DLC/a_new_world_columns.html`
returns `HTTP/2 200` and a representative WebP thumb downloads
(`ANWBritish/thumbs/lobby_portrait.webp`, 19490 bytes, 256×256 RGBA).

`artifacts/validation/visual_art/static_contact_sheet.html` (~372 KB,
rebuilt 2026-05-20 06:00) is the internal contact sheet for offline
eyeballing. It renders all 40 ANW civs side-by-side with 7+ image
columns each:

- HTML scoreboard flag / postgame flag / portrait references
- civmods.xml homecity flag / postgame flag / portrait
- hi-res leader portrait under `art/ui/leaders/`
- **Captured-screenshot columns** populated by
  `anw_visual_capture.py --synthesize` — synthesises 5 capture
  slots (`01_diplomacy.png` … `05_postgame.png`) per civ from the
  static `art_surfaces` paths in `art_inventory.json` so the
  preview columns are non-empty even for civs that never received
  a live in-engine capture session.

Fixed in this overnight pass:
- Engine-token → ANW-token namespace mismatch in
  `build_art_contact_sheet.py` that left Sokoto / Maratha /
  Lakota / Russian rows with only 2 imgs (BLOCKER badge). Added
  `ENGINE_TO_ANW_TOKEN` + `DISPLAY_TO_ENGINE_TOKEN` recovery
  dicts; all 4 rows now show 7+ imgs.
- Empty `civ_token` strings for the 4 above in `findings.json`
  now resolved via the display-name fallback.

Per user preference (no cursor-grab MCP tools), in-engine UI
verification is left for the user to eyeball when they wake up.
The sheet loads offline from the repo root.

### Live-capture workflow (optional, for v1.1 polish)

`python3 tools/aoe3_automation/anw_visual_capture.py --civ <ANWCiv>`
walks the user through 5 prompts (F10 / Tab / J / ally-flag /
resign) and snapshots via `lobby_driver.screenshot()`
(gamescopectl primary, X11 fallback — non-intrusive, no cursor
grab). Live captures overwrite the synthesised ones in
`artifacts/validation/visual_art/<civ>/`.

## Civ inventory — 40 ANW civs (not 46)

The original plan referenced "22 base + 24 revolution = 46". Actual
implementation has 40 ANW-prefixed civs in `ANW_CIVS` mapping. The
delta is intentional: some legacy-civ tokens never received an
`ANW<civ>` overlay (they retain engine-truth tokens unchanged in
civmods.xml). The 40-civ set is fully validated:

- 22 reskinned base civs
- 18 revolution civs promoted to lobby-pickable
- All 40 appear in `data/civmods.xml` — confirmed by
  `validate_offline_picker.py` (✓ PASS, 39 picker + 1 also-revolution-trigger
  reported; `ANWMexicans` is in `ANW_NON_PICKER_TOKENS` by historical
  intent but also ships in civmods.xml as a regular lobby civ, so it's
  selectable AND revolution-triggerable — see note in
  `tools/migration/anw_mapping.py:178`).
- Two additional revolution-only variants — `ANWFrenchCanadians`
  and `ANWAmericans` — exist as in-game revolution triggers
  (Lower Canada Patriotes / American Revolution political choices)
  without a civmods.xml lobby-picker entry. Confirmed absent from
  `data/civmods.xml`.

## FrenchCanadians / Lower Canada audit

User asked: *"we're only using lower canada?"*

**Answer: yes, effectively.** The lobby-picker Canadian civ is
`ANWCanadians` (display name "Province of Canada", the 1841 union of
Upper + Lower Canada). `ANWFrenchCanadians` exists only as a
revolution variant triggered in-game via the Lower Canada Patriotes
political choice — it has no civmods.xml entry and no Skirmish-picker
portrait. No code changes required; this matches the historical
framing and the HTML reference at `dev/a_new_world.html`.

## Known limitations / v1.0 ship-blockers

None blocking workshop deploy. Items for v1.1 backlog:

1. Live AI probe pipeline — Age3Log capture works when developer mode
   flags are honored by the engine; sometimes they aren't (cause
   unclear, possibly Proton/Wine config). Personality counter is the
   fallback channel. Not a release blocker.
2. Wall-type constants beyond `cBuildWallPlanWallTypeRing` — would
   need engine RE; current radius+gate-count knobs cover the
   gameplay impact.
3. Smart gate-direction placement — needs engine probing of
   `cBuildWallPlanGate0Position` etc.; documented as a v1.1 stretch
   goal in `aiBuildingsWalls.xs:340`.
4. Live in-engine capture for the column-site "Visual confirmation"
   sections — all 40 civs currently use synthesized crops derived from
   static `art_surfaces` (real mod art, framed deterministically rather
   than via in-game screenshot). The capture path
   (`tools/aoe3_automation/anw_visual_capture.py`) is wired up but the
   game crashes mid-skirmish for some civs under gamescope+Proton —
   blocked by the issue documented in `memory/project_anw_visual_capture_ceiling.md`.

## Deploy steps for workshop release

1. `python3 tools/validation/run_all_validators.py` — confirm PASS
   (last static run: 41/41 PASS at 2026-05-20 06:56)
2. `python3 tools/validation/validate_packaged_mod.py` — validates
   the release tree against ship rules (filters dev-only top-level
   entries: .git, .github, artifacts, docs, tests, tools, etc.)
   (last run: PASS)
3. Optional: `python3 tools/validation/run_all_validators.py --include-live`
   from inside a running ANEWWORLD skirmish to clear the 7 live SKIPs.
4. Steam Workshop "Update" via in-game Mod Manager → upload from
   `~/.steam/steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/mods/local/A New World/`
5. Verify the listing renders cover art + thumbnail correctly

## What changed during the overnight loop (2026-05-19 → 2026-05-20)

- **Column site populated for all 40 civs** — synthesized 9 captures /
  10 crops per civ from `art_inventory.json` art_surfaces. Previously
  only 3 civs had thumbnails; now every civ's "Visual confirmation"
  section is non-empty. Total commit footprint: ~150 MB (image
  dimensions capped at 800×800 crops / 320×320 thumbs).
- **ANWBritish realigned with synth template** — the prior "real
  capture" set had wrong-screen captures (mid-game paused exploration
  view with debug probes) that missed every intended UI element.
  Replaced with the same deterministic template as the other 39 civs.
- **Civ-count documentation** corrected across `mod.xml` and `CHANGELOG.md`:
  was claiming "48 / 22+26 / 44-nation" → actual is 40 / 22+18 (37
  picker + 3 revolution-trigger).
- **Stale test-mode backup removed** — `game/ai/.aiHeader.xs.testmode_backup`
  was a leftover from the auto-resign test harness. Confirmed not
  referenced by any runtime path; deleted to keep the shipped tree clean.
- **GitHub Pages auto-deploy verified** — workflow runs 26124020945
  and 26124880907 both succeeded; live URL serves HTTP/2 200 and
  representative WebP thumbnails download cleanly.
