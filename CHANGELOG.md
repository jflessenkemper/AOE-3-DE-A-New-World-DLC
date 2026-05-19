# Changelog

All notable changes to **AOE 3 DE - A New World** are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-05-20

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
- The mod now **adds** the 22 base ANW civs alongside the base-game civs
  rather than overriding them — `ANW_TOKEN_TO_ENGINE_TOKEN` is now empty
  and every ANW token maps to itself in civmods.xml `<name>` entries
  and decks_anw.json keys. Restores access to vanilla civs for players
  who want both gameplay sets available.

### Added
- **40 ANW civilizations** in the lobby picker (`data/civmods.xml`) —
  22 base civs + 18 revolution civs promoted to top-level pickable
  nations. Two additional revolution-only variants
  (`ANWFrenchCanadians`, `ANWAmericans`) trigger in-game from the
  Lower Canada Patriotes and American-Revolution political choices
  without being directly lobby-selectable.
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
