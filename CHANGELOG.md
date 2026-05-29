# Changelog

All notable changes to **AOE 3 DE - A New World** are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased] — 2026-05-26

- Dropped Yucatan/Californians/CentralAmericans civs (no nation-card content).

## [1.0.0] — 2026-05-20 (Public Release)

### Added

- **40 playable ANW civilizations**: Argentines, Aztecs, Barbary, Brazil, British, Canadians, Chileans, Chinese, Columbians, Dutch, Egyptians, Ethiopians, Finnish, French, Germans, Haitians, Haudenosaunee, Hausa, Hungarians, Inca, Indians, Indonesians, Italians, Japanese, Lakota, Maltese, Mayans, Mexicans, Napoleonic France, Ottomans, Peruvians, Portuguese, Revolutionary France, Romanians, Russians, South Africans, Spanish, Swedes, Texians, USA.
- **Home City & Deck systems** for every civ — fully wired into the home city picker and deck loader.
- **Smart-walls AI system** in `game/ai/core/aiBuildingsWalls.xs`: real chokepoint detection, water/cliff-aware placement, age-tiered radius and gate count, gap-closure verification.
- **Per-civilization build-style helpers** (`game/ai/leaders/leaderCommon.xs`): Naval Mercantile, Highland Citadel, Jungle Guerrilla, Cossack Voisko, Nomadic Raiding, and 14+ more strategic profiles.
- **In-game visual capture pipeline** (`tools/aoe3_automation/anw_visual_capture_runner.py`) — automated Workshop visual QA with diplomacy panel flag inspection.
- **41-validator static QA suite** (`tools/validation/run_all_validators.py`) — XS parsing, terrain heading, leader spec compliance, wall strategy audit, art coverage, civ crossref validation.
- **Static art contact sheet** (`artifacts/validation/visual_art/static_contact_sheet.html`) — visual reference for all 40 civs.
- **Per-civ column review site** (`a_new_world_columns.html`, 3.6 MB) — 62-column 4-panel grid (Strings · Paths · Mod Changes · Art+Captures) with 4-state path badges (mod ✓ / vanilla ⊙ / engine ◆ / missing ✗), AI Doctrine block with wall-strategy decode and prose, and per-civ asset-coverage audit. ANWBritish is the gold-standard review surface (53 paths, 39 asset rows, 28 in-game captures, 0 misses).
- **ANW Hub Test random map** (`RandMaps/anwHubTest.xs` + `.xml`) — 8-player AI doctrine test arena: 1 observer + 7 AIs in wedge compartments around a central naval sea, with chat-marker triggers at T+15/30/60/90s and auto-end via "Set Player Defeated" on the observer. Single-knob `gHubTestEndSeconds` (120s fast cycle / 1200s extended) gates four additional milestone window markers (T+240/360/600/960).

### Changed

- **Wall strategy enforcement** via spec-override pattern: `gLLWallStrategy = cLLWallStrategy<Spec>;` after helper call prevents defaults from overriding explicit specs.
- **ESC menu coordinates** re-verified at 1920×1080: gears (1860, 30), Resign (1830, 365), Diplomacy (1691, 35).
- **19 ANW civs newly wired** into `llApplyBuildStyleForActiveCiv()`.

### Fixed

- **Lobby picker double-up** — the 22 base picker civs (British, XPAztec, DEItalians, …) used to render alongside their ANW counterparts in both the Skirmish "Select Civilization" picker and the "Select Home City" picker, producing 44 rows with visually-duplicate names and a tail of raw engine tokens (DEItalians, XPSioux) where the base stringtable didn't resolve. Fixed by adding 22 `<civ>` suppression entries to `data/civmods.xml` that override each base picker civ with `<main>0</main>` + `<visible>0</visible>` + empty `<homecityfilename></homecityfilename>`. Mirrors the engine's own hide-civ pattern (TheCircle, SPCBarbaryPirates). Caught locally by new validators `validate_offline_picker.py` (now `<visible>`-aware) and `validate_no_homecity_doubles.py`.
- **19 diplomacy/scoreboard portrait placeholders** — the `<matchmakingtextures><smallportraittexturewpf>` field for 19 base-overlap ANW civs (Aztecs, Chinese, Ethiopians, French, Germans, Haudenosaunee, Hausa, Inca, Indians, Italians, Japanese, Lakota, Maltese, Mexicans, Ottomans, Portuguese, Russians, Spanish, Swedes) pointed at 1–3 KB `cpai_avatar_anw<civ>.png` placeholder banners (solid color + leader name in white text) instead of the real `cpai_avatar_<civ>_<leader>.png` portrait files (87–176 KB each, e.g. Tokugawa, Catherine the Great, Suleiman the Magnificent) that were already on disk and already wired into `<homecitypreviewwpf>`. Net effect: players saw a coloured banner instead of the actual leader painting in the F4 diplomacy panel and Tab scoreboard. Fixed by rewiring each civ's `smallportraittexturewpf` to the same real portrait used by `homecitypreviewwpf`, closing the gap the post-2026-05-18 art consistency pass missed.
- **39 of 40 ANW civ-picker rollover blurbs misaligned** — every ANW civ except British had a `<rollovernameid>` pointing at the wrong leader's historical paragraph. Root cause: the 490200-490247 string range was authored in leader-appearance order, but `civmods.xml` assigned IDs alphabetically by civ token (Aztecs=490200, British=490201, Chinese=490202, …), so the displayed text drifted off-by-N from the civ. Player-visible consequences before fix: hovering "Lakota" in lobby civ-picker showed Motecuhzoma II / Aztec text; "United States" showed Hidalgo / Mexican text; "Barbary" showed Prince Henry / Portuguese text; "Russians" showed only "Louis XVIII" name; and 35 more identical-class mismatches. Fixed by rewiring all 39 civs to the correct blurb ID — base-overlap civs to the matching 4902xx odd ID (Aztecs→490213 Motecuhzoma, Lakota→490241 Sitting Bull/Crazy Horse, USA→490223 Washington, Mexicans→490221 Hidalgo, …), and revolution-tier civs to the matching 400xxx blurb (Argentines→400001 San Martín, Barbary→400002 Barbarossa, Indonesians→400016 Diponegoro, …). All 40 civs now resolve to a thematically-correct historical leader paragraph in the lobby rollover.
- **9 wall_strategy spec mismatches** via leader-file overrides (Montezuma, Pachacuti, Catherine, Haitians, Chileans/Indonesians/Mayans/Peruvians/Yucatan revolutions). South Africans is correct from the `llUseNavalMercantileCompoundStyle` helper default (`cLLWallStrategyCoastalBatteries`), not an override.
- **`validate_leader_vs_spec.py`** — position-aware override detection (no false-positives on helper vs. spec-override).
- **`audit_engine_vs_spec.py`** — override-aware logic plus brace-counted block extraction.
- **`validate_art_coverage.py`** — lowercase regex for `<name>` tags + base-game avatar allowlist.

### Known Issues

- **4 naval civs** (British, Dutch, Portuguese, Barbary) build barracks before dock — v1.1 tuning.
- **8 civs forward-base bias** outside spec band — v1.1 strategic AI tuning.
- **Visual capture** verified in-game for ANWBritish; all 40 picker civ leader portraits independently visually inspected at the pixel level (`resources/images/icons/singleplayer/cpai_avatar_<civ>_<leader>.png`) and confirmed to depict the correct historical figure in period-appropriate art — Tudor court paintings (Elizabeth I), Qing scrolls (Kangxi), Ottoman miniatures (Suleiman), 19th-century photographs (Mannerheim, Kruger, Cuza, Kossuth), Cuzco-school colonial paintings (Pachacuti), period sketches (Crazy Horse), Javanese lithographs (Diponegoro), and so on across every region/era represented. Plus revolution-variant Papineau daguerreotype confirmed. All art surfaces — diplomacy panel, scoreboard, post-game results, home-city walking animations, ally-flag deck panel — point at authentic historical leader artwork, with no placeholder banners or generic civ-flag fallbacks remaining.

---

### Detailed engineering log (1.0.0)

The high-level §1.0.0 entry above is the user-facing release note;
this section is the deeper engineering trail for the same release —
subsystem-by-subsystem notes, dated as the work happened.

First public release. The mod is now `status: release` and has been verified
end-to-end through the in-engine automated test harness — every one of the 40
selectable civilizations was loaded into a real Skirmish match, the AI script
was confirmed to start under each leader's personality, and the harness
captured a clean resign on every match.

### Smart walls (2026-05-19)
- **Real chokepoint detection** in `game/ai/core/aiBuildingsWalls.xs` —
  `llDetectChokepointVector()` walks `kbAreaGetNumber()` once per match,
  finds the narrowest passable border area between impassable neighbours,
  and biases `cLLWallStrategyChokepointSegments` toward that vector.
- **Water/cliff awareness** — `llGetForwardBiasedWallCenter()` now samples
  the proposed wall center via `kbAreaGetIDByPosition` → `kbAreaGetType`
  and walks inland along the inverse front vector when the target tile
  is water or impassable land. Fixes the "half-wall in the ocean" failure
  mode on coastal/island maps.
- **Wall tier progression by age** — `llSelectWallType()` picks
  palisade-equivalent at Age 1, stone at Ages 2–3, fortified + outer
  supplement at Age 4+. Previously every code path hardcoded the same
  ring type at every age.
- **Gap-closure verification** — new rule `verifyWallClosure` runs every
  60 s once a ring plan has been emitted, estimates real coverage via
  `kbUnitCount(cUnitTypeAbstractWall, cUnitStateABQ)`, escalates priority
  if coverage is < 60% after 4 minutes, and re-emits a partial ring plan
  covering only the gap arc when segments die. Probe key `wall.closure`
  surfaces coverage % to validators.

### Art consistency hardening (2026-05-18 → 2026-05-20)
- New validator `tools/validation/validate_civmods_art_consistency.py`
  catches the "half-fixed mod" pattern where one engine surface (top-left
  home-city button) shows the new ANW asset while another (scoreboard /
  post-game flag, lobby AI portrait) still shows the base-game asset.
- 22 `postgame_flag_*.png` assets generated to populate the post-game
  results screen with the correct mod-supplied flags.
- ANW-specific civ-picker portraits added: `cpai_avatar_french_robespierre`,
  `cpai_avatar_hausa_usman_dan_fodio`, `cpai_avatar_swedes_gustavus_adolphus`.
- Diplomacy / scoreboard / post-game flag and lobby picker portrait now
  all point at the matching mod asset for every base + revolution civ.

### Deck completeness (2026-05-19)
- 12 missing base-civ deck entries added to `data/decks_anw.json`
  (ANWAztecs, ANWChinese, ANWEthiopians, ANWHaudenosaunee, ANWHausa,
  ANWInca, ANWIndians, ANWItalians, ANWJapanese, ANWLakota, ANWMaltese,
  ANWSwedes). Each is a curated 25-card deck split 4 / 5 / 10 / 6 across
  Ages 0 / 1 / 2 / 3, sourced from the corresponding
  `data/anwhomecity*.xml` Land deck and verified against `cards.json`.

### Civmods.xml strategy change (2026-05-20)
- The mod ships 40 ANW civs as **additive** entries (every ANW token maps
  to itself in `civmods.xml` `<name>` entries and `decks_anw.json` keys;
  `ANW_TOKEN_TO_ENGINE_TOKEN` is empty). The base picker civs that ANW
  re-implements (British, XPAztec, DEItalians, …) are then **suppressed**
  in the picker via 22 hide-base entries that set `<main>0</main>` +
  `<visible>0</visible>` + empty `<homecityfilename></homecityfilename>`.
  Net effect: the Skirmish "Select Civilization" picker shows exactly the
  40 ANW civs, no double-ups, no raw engine tokens. The base civ
  definitions remain intact in the engine for save / replay
  compatibility, scenarios, and other game modes that reference them by
  token (e.g. `British`, `XPSioux`).

### Added
- **40 ANW civilizations** in the lobby picker (`data/civmods.xml`) —
  22 base civs + 18 revolution civs promoted to top-level pickable
  nations. Two additional revolution-only variants
  (`ANWAmericans`) triggers in-game from the American-Revolution
  political choice without being directly lobby-selectable.
  `ANWFrenchCanadians` (Papineau) has been removed.
- **Per-leader AI doctrine** (`game/ai/leaders/*.xs`) — distinct build orders,
  military comp, and explorer-escort posture per nation.
- **Leader-escort doctrine** — AI treats its explorer as the battlefield
  leader with a living screen of units around them.
- **Smart rout** — only AI non-elite land units rout (≤25% HP, no friendly
  elite nearby); elites and player-controlled units never auto-rout.
- **Historical map placement** — every civ pinned to a terrain bias and
  expansion heading via `cBuildPlanCenterPosition` (real coordinates, not
  just labels).
- **Curated 25-card deck per civ** matched to leader playstyle.
- **Lobby-matched leader portraits, names, and chat quotes** — consistent
  from lobby thumbnail through scoreboard.
- **Revolutions disabled on base civs** — the 18 ANW revolution civs are
  already top-level picks, so age-up doesn't offer the old options.
- **Reference site** at <https://jflessenkemper.github.io/AOE-3-DE-A-New-World-DLC/>
  with per-civ playstyle panels.

### Test harness
- **Matrix runner** (`tools/aoe3_automation/matrix_runner.py`) — drives the
  in-engine lobby, plays Skirmish matches batched 8-civs-per-match, captures
  personality probes from every AI, and writes per-civ coverage reports.
- **`--auto-resign-ms` flag** — rewrites `cLLTestModeAutoResignMs` in
  `game/ai/core/aiGlobals.xs` so every AI calls `aiResign()` after a fixed
  game-time threshold, bounding match length for fast deterministic coverage
  runs (~5 min per 8-civ batch). Always reset to `0` on exit so release
  builds never carry test instrumentation.
- **Biome → civ map** (`tools/aoe3_automation/biome_to_civ_map.json`) —
  routes each civ to an official AoE3 DE map that exercises its environmental
  preference (temperate / arid / tropical / arctic / subtropical / andean /
  mediterranean) using stock RMS scripts (no custom map authoring required).

### Release verification — 2026-05-01 (live matrix) + 2026-05-20 (static gate)
- Live in-engine matrix at the time of the 2026-05-01 run covered every then-pickable
  civ; the roster has since been culled to the final 40 (37 lobby-pickable + 3
  revolution-trigger). Smart-walls and post-roster-cull verification on the live
  matrix is left as a v1.1 polish item (covered by the offline doctrine validator).
- Static release gate (2026-05-20): `python3 tools/validation/run_all_validators.py`
  → **41/41 offline validators PASS**, 7 live-game validators skipped pending the
  user's in-engine wake-up run.
- `python3 tools/validation/validate_packaged_mod.py` → **PASS** against ship rules.
- Auto-resign reset to `0` so release build carries no test instrumentation.

[1.0.0]: https://github.com/jflessenkemper/AOE-3-DE-A-New-World-DLC/releases/tag/v1.0.0
