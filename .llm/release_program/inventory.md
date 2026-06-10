# ANW Release Program Inventory

**Generated:** 2026-06-08  
**Scope:** Read-only audit of existing validators, documentation, screenshots, and tooling.

---

## 1. Existing Validators

### Core Static Validators (`tools/validation/validate_*.py`)

Over **130 validators** exist across multiple categories. Key ones:

| Validator | Purpose |
|-----------|---------|
| `validate_civ_loadability.py` | Every ANW civ loads in-game without error |
| `validate_civmods_art.py` | HTML art references match data/civmods.xml wiring |
| `validate_civ_crossrefs.py` | All cross-references (techs, units, buildings) resolve |
| `validate_art_consistency.py` | Leader portraits visually consistent |
| `validate_art_coverage.py` | Portrait coverage for every personality |
| `validate_art_pixel_perfect.py` | Pixel-perfect static art verification |
| `validate_doctrine_compliance.py` | Runtime probes vs doctrine globals alignment |
| `validate_homecity_cards.py` | Home-city card deck integrity |
| `validate_homecity_leader_match.py` | Each home city's heroname resolves correctly |
| `validate_html_reference.py` | a_new_world.html structural integrity |
| `validate_html_vs_mod.py` | HTML reference vs actual mod data sync |
| `validate_hub_test_coverage.py` | anwHubTest.xs covers all spec milestones |
| `validate_icon_path_existence.py` | Every icon/portrait/flag path resolves |
| `validate_no_homecity_doubles.py` | No civ duplication in HC picker |
| `validate_no_locid_duplicates.py` | No duplicate _locID in stringmods.xml |
| `validate_no_orphan_xml.py` | No orphan shadow XML files |
| `validate_offline_matrix.py` | Run all offline checks per-civ in one pass |
| `validate_offline_picker.py` | Predict live skirmish picker output |
| `validate_per_age_v2.py` | Per-age + walling doctrine vs telemetry |
| `validate_per_civ_wall_knobs.py` | llSetWallKnobsForCiv() exercise all 40+ civs |
| `validate_personality_active.py` | Every civ has active .personality file |
| `validate_personality_lobby.py` | Each personality has consistent lobby quadruple |
| `validate_personality_overrides.py` | Personality display-name overrides work |
| `validate_personality_vs_spec.py` | Personality probes vs playstyle_spec.json |
| `validate_playstyles.py` | Actual vs expected civ behaviors (Playstyle Engine) |
| `validate_techtree.py` | Tech tree coherence and completeness |
| `validate_xs_scripts.py` | XS script syntax and references |
| `validate_civ_tech_resolution.py` | Every tech-name reference resolves |
| `validate_deck_card_effects.py` | Shipped deck cards have effects in techtreemods |
| `validate_blurb_coverage.py` | Catch stale/incomplete blurbs + template text |
| `validate_age_up_politicians.py` | Free-age-up exploits + politician options |
| `validate_ai_behaviour_map.py` | ai_behaviour_map.json spec match check |
| `validate_ai_playstyle.py` | HTML playstyle prose vs playstyle_spec.json |

**Full list:** 130+ validators under `/tools/validation/validate_*.py`  
**To avoid duplication:** Check this file before building new validators. See `run_all_validators.py` for orchestration.

---

## 2. Wiki / Documentation

**Wiki location:** `/docs/wiki/` ✓ **EXISTS**

### Top-level wiki docs:
- `README.md` — Wiki overview + architecture TOC
- `additive-data-mods.md` — How custom data mods work
- `community-tools.md` — External tool integration notes
- `mod-folder-structure.md` — ANW repo layout explanation
- `multi-civ-architecture.md` — How 43+ civs coexist in one mod
- `replays-scenarios.md` — Replay format + custom scenario authoring
- `ai-layer/` — AI personality + doctrine design docs
- `data-layer/` — XML schema + civmods structure
- `file-formats/` — Binary format specs (DDT, replay, etc.)
- `modding-pitfalls/` — Common mistakes + gotchas
- `ui-layer/` — Home city picker, portrait rendering, etc.
- `validation/` — Validator architecture

### Top-level `/docs/` files:
- `CARD_INDEX.txt` — Index of all homecity cards
- `NEW_NATIONS_DESIGN.md` — Design spec for all 43 ANW civs
- `RELEASE_QA_PLAN.md` — Release validation roadmap
- `REALISM_MODE_DESIGN.md` — Realism mode features + balance
- `SIM_FARM_IMPLEMENTATION_PLAN.md` — Doctrine sim architecture
- `SPEC_V2_SCHEMA.md` — Playstyle spec JSON schema
- `STATE_OF_THE_MOD.md` — High-level status snapshot
- `TEST_COVERAGE_PLAN.md` — Validator + test matrix
- `design/` — Scenario design, AI design docs
- `engine/` — Engine integration notes

**Status:** Wiki dir exists with good coverage; no missing structure.

---

## 3. Per-Nation Screenshot Coverage

### Total Civ Count: 43 ANW civs + 1 placeholder
**Visual art base:** `/artifacts/validation/visual_art/`

| Civ | Total PNGs | Full Subdir | Buildings Subdir | Status |
|-----|-----------|------------|------------------|--------|
| ANWArgentines | 7 | full:2 | — | Partial |
| ANWAztecs | 7 | full:2 | — | Partial |
| ANWBarbary | 7 | full:2 | — | Partial |
| ANWBrazil | 7 | full:2 | — | Partial |
| **ANWBritish** | **54** | **full:34** | **buildings:20** | **Full** |
| ANWCanadians | 9 | full:4 | — | Partial |
| ANWChileans | 7 | full:2 | — | Partial |
| ANWChinese | 7 | full:2 | — | Partial |
| ANWColumbians | 7 | full:2 | — | Partial |
| ANWDutch | 7 | full:2 | — | Partial |
| ANWEgyptians | 7 | full:2 | — | Partial |
| ANWEthiopians | 7 | full:2 | — | Partial |
| ANWFinnish | 7 | full:2 | — | Partial |
| ANWFrench | 7 | full:2 | — | Partial |
| ANWGermans | 7 | full:2 | — | Partial |
| ANWHaitians | 7 | full:2 | — | Partial |
| ANWHaudenosaunee | 7 | full:2 | — | Partial |
| ANWHausa | 7 | full:2 | — | Partial |
| ANWHungarians | 8 | full:2 | — | Partial |
| ANWInca | 8 | full:2 | — | Partial |
| ANWIndians | 8 | full:2 | — | Partial |
| ANWIndonesians | 7 | full:2 | — | Partial |
| ANWItalians | 7 | full:2 | — | Partial |
| ANWJapanese | 7 | full:2 | — | Partial |
| ANWLakota | 7 | full:2 | — | Partial |
| ANWMaltese | 7 | full:2 | — | Partial |
| ANWMayans | 7 | full:2 | — | Partial |
| ANWMexicans | 7 | full:2 | — | Partial |
| ANWNapoleonicFrance | 8 | full:2 | — | Partial |
| ANWOttomans | 7 | full:2 | — | Partial |
| ANWPeruvians | 7 | full:2 | — | Partial |
| ANWPortuguese | 7 | full:2 | — | Partial |
| ANWRevFrance | 7 | full:2 | — | Partial |
| ANWRomanians | 7 | full:2 | — | Partial |
| ANWRussians | 7 | full:2 | — | Partial |
| ANWSouthAfricans | 7 | full:2 | — | Partial |
| ANWSpanish | 7 | full:2 | — | Partial |
| ANWSwedes | 7 | full:2 | — | Partial |
| ANWTexians | 7 | full:2 | — | Partial |
| ANWUSA | 7 | full:2 | — | Partial |
| **allies** | **0** | — | — | **Missing** |

**Summary:**
- **40 civs:** 7-9 PNGs each (lobby portrait + ~6 art surfaces + building shots)
- **1 civ (ANWBritish):** 54 PNGs — full multi-building surface capture (aged out)
- **1 placeholder (allies):** 0 PNGs — needs creation
- **Total PNGs across repo:** 2430 files
- **Critical gap:** 2 civs (RioGrande, BajaCalifornians) in civmods.xml have NO screenshot folders at all

---

## 4. Release Readiness Site

**File:** `/artifacts/validation/release_readiness_site.html`  
**Built by:** `tools/validation/build_release_readiness_site.py`  
**Last updated:** 2026-06-08 18:37

### Per-Nation Surfaces/Columns Rendered:

The site renders a **multi-column table per civ** with:

**Art Surfaces block (10 images):**
- Lobby portrait (leader headshot)
- Loading flag
- Home city button icon
- HUD flag (corner)
- Home city scene (full background)
- Tech tree overview row
- Diplomacy panel
- Scoreboard player row
- ESC menu player summary
- Endgame flag

**In-game screenshot strip (8+ columns):**
Canonical column slots (with fallback filenames):
1. `01_menu` / `01_menu_select_civ.png`
2. `02_hud_default` / `03_hud.png`
3. `03_home_city` / `04_home_city.png`
4. `04_unit_roster` / `05_units.png`
5. `05_age2` / `06_age2.png`
6. `06_age3` / `07_age3.png`
7. `07_military` / `08_military.png`
8. `08_endgame` / `09_endgame.png`
Plus **extras strip** for uncategorized captures.

**Metadata columns (per-civ card):**
- Civ token (e.g. `ANWFrench`)
- Display name + leader name
- Culture type (Western Europe, Aztec, etc.)
- Playstyle summary (from playstyle_spec.json)
- Wall doctrine strategy (fortress ring, etc.) + color indicator
- Doctrine globals (military focus, trade bias, etc.)
- Age-up tech + politician roster
- Home city card preview + card deck listing
- Revolution paths (if any)
- Validator gate status (pass/warn/fail icons)

---

## 5. Nation + Building Maps

### Existence Verification:

✓ **`/artifacts/validation/per_civ_building_checklist.md`** — 25 KB  
✓ **`/artifacts/validation/per_civ_building_capture_map.json`** — 58 KB  

### Content Summary:

**Cultures:** 12 (one per architecture style)
- WesternEurope, Mediterranean, EasternEurope (11 buildings each)
- Aztec (6), Chinese (9), Indian (10), Japanese (11), Iroquois (8), Sioux (7)
- Inca (8), AfricaEast (9), AfricaWest (9)

**Buildings per culture:** 6–11 (Town Center → Capitol progression)

**ANW Civs (43 total) mapped to cultures in `data/civmods.xml`:**

| Civ | Culture |
|-----|---------|
| ANWArgentines | WesternEurope |
| ANWAztecs | Aztec |
| ANWBarbary | Mediterranean |
| ANWBrazil | WesternEurope |
| ANWBritish | WesternEurope |
| ANWCanadians | WesternEurope |
| ANWChileans | WesternEurope |
| ANWChinese | Chinese |
| ANWColumbians | WesternEurope |
| ANWDutch | WesternEurope |
| ANWEgyptians | AfricaEast |
| ANWEthiopians | AfricaEast |
| ANWFinnish | EasternEurope |
| ANWFrench | WesternEurope |
| ANWGermans | WesternEurope |
| ANWHaitians | WesternEurope |
| ANWHaudenosaunee | Iroquois |
| ANWHausa | AfricaWest |
| ANWHungarians | EasternEurope |
| ANWInca | Inca |
| ANWIndians | Indian |
| ANWIndonesians | Indian |
| ANWItalians | Mediterranean |
| ANWJapanese | Japanese |
| ANWLakota | Sioux |
| ANWMaltese | Mediterranean |
| ANWMayans | Aztec |
| ANWMexicans | Aztec |
| ANWNapoleonicFrance | WesternEurope |
| ANWOttomans | Mediterranean |
| ANWPeruvians | Inca |
| ANWPortuguese | WesternEurope |
| ANWRevFrance | WesternEurope |
| ANWRomanians | EasternEurope |
| ANWRussians | EasternEurope |
| ANWSouthAfricans | WesternEurope |
| ANWSpanish | WesternEurope |
| ANWSwedes | WesternEurope |
| ANWTexians | WesternEurope |
| ANWUSA | WesternEurope |

**Data sources verified:**
- `/data/civmods.xml` — Canonical ANW civ definitions
- `/artifacts/roster_audit/base_data/techtree.xml` — Base building proto refs
- `/artifacts/roster_audit/base_data/civs.xml` — Base civilization data
- `/artifacts/roster_audit/base_data/proto.xml` — Unit/building prototypes

---

## 6. Harness + XS Sim Speed-Up Candidates

### Harness (`tools/aoe3_harness/`)

**Current:** Compositor-based socket pipeline (Phase 6 verified).

**Speed-up opportunities:**

1. **Parallel screenshot batching** — `harness_client.py` sends SCREENSHOT sequentially; batch N civs' captures to run in parallel across multiple game instances (requires socket multiplexing or subprocess pooling).

2. **Hot-reload caching** — `hotreload.py` watches XS/XML on 1s stat() polling; adopt `inotify_simple` (already documented) or similar event-driven watcher to eliminate polling latency.

3. **Smoke test socket reuse** — `smoke_socket.py` creates fresh socket per test; reuse a single persistent connection for probe batches.

4. **Screenshot path caching** — `capture.py` resolves screenshot paths on every call; cache the last N known-good paths to eliminate repeated disk lookups.

5. **Doctrine bisect binary search optimization** — `git_bisect_helper.py` runs full probe per commit; memoize probe results (timestamp-based, invalidate on XS change).

### XS Sim (`tools/xs_sim/`)

**Current:** Tree-walker interpreter (95% language coverage, 85% decision logic).

**Speed-up opportunities:**

1. **Parse caching** — `parser.py` re-parses leader files on every run; serialize AST to `.pyc` or JSON cache, invalidate on civmods.xml timestamp change.

2. **Interpreter bytecode compilation** — Tree-walker is slow; compile AST to a simple bytecode format + bytecode VM (estimated 3–5x speedup for doctrine simulation).

3. **Builtin mocking batching** — `builtins.py` creates fresh GameState per leader; reuse a baseline state, snapshot-and-restore per civ to avoid repeated initialization.

4. **Parallel leader execution** — `harness.py` runs leaders serially; spawn worker pool (multiprocessing.Pool) with per-worker GameState to parallelize 26 leader files.

5. **Rule scheduler batch-fire optimization** — `interpreter.py` fires rules individually; collect rules due at next tick, fire N in one batch iteration (minor, but measurable for 100+ rules).

---

## Summary: Key Findings

**Screenshot Coverage:**
- **40/43 civs:** Baseline art surfaces captured (7–9 PNGs each)
- **1/43 civs (British):** Full multi-building surface set (54 PNGs)
- **2/43 civs:** No screenshots (RioGrande, BajaCalifornians) — missing folders entirely
- **1 placeholder:** `allies/` is empty — likely deprecated

**Documentation:**
- Wiki structure solid and covers all major layers (AI, data, UI, validation, file formats)
- Release QA plan exists; see `/docs/RELEASE_QA_PLAN.md`

**Validators:**
- 130+ existing validators across static checks, runtime probes, and in-engine verification
- Well-organized; avoid building duplicates without checking `run_all_validators.py`

**Tooling:**
- Harness: mature, Phase 6 verified, socket-based, non-invasive
- XS Sim: 95% language coverage, 26/26 leaders parse, 24/24 leaders execute
- Multiple speed-up paths available (parallelization, caching, bytecode) for both

**Readiness site:** Renders 10 art surfaces + 8 screenshot columns + metadata per civ; HTML is up-to-date (2026-06-08).
