# ANW v1.0 — Test Coverage Plan: 85% → 100%

**Generated:** 2026-05-26  
**Current gate:** 42/49 PASS, 0 FAIL, 7 SKIP (7 SKIPs are live-game validators requiring `--include-live`)  
**Honest coverage estimate:** ~85% of static risks caught; runtime behaviors, multiplayer determinism, save/load, and install-flow remain unvalidated by automation.

---

## 1. Gap Analysis

The following table covers every failure mode that could embarrass a v1.0 launch player. For each, it maps to (a) the static validator that catches it, (b) the runtime validator, and (c) the launch risk if shipped uncaught.

### 1.1 Visual Art

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| Missing/wrong DDT header format (format byte vs body size) | `validate_ddt_format.py` — PASS | None | AI portrait blanks in lobby (confirmed bug 2026-05-12) |
| Art surface key mismatch across civmods fields (flag button vs scoreboard vs portrait) | `validate_civmods_art_consistency.py` — PASS | None | Napoleon shows NE Empire flag on button, Bourbon on scoreboard |
| Art pixel dimensions out of spec (512x512 portrait, wrong aspect ratio) | `validate_art_pixel_perfect.py` — PASS (warns on 25 hires) | None | Stretched/squished portraits in-game |
| Missing art file for some civ surfaces (DDT absent from mod tree and base .bar) | `validate_civ_asset_existence.py` — PASS | None | Black squares or fallback art |
| Art coverage gaps — civ has entry in civmods but no portrait in art_inventory | `validate_art_coverage.py` — PASS | None | Invisible slot in picker |
| Home city visual asset references broken (visual/pathdata/camera/ambientsounds) | `validate_homecity_assets_exist.py` — PASS | None | Black/empty home city scene |
| **GAP: In-game rendering fidelity** (does portrait actually render correctly at 1920x1080 in the live game?) | **None** | `validate_visuals.py` (SKIP — needs runtime artifact) | Artist errors invisible in static check (wrong color space, alpha, mipmap level) |
| **GAP: Per-civ age-up dialog art** (politician banner, age-select overlay) | **None** | **None** | Age-up dialog shows default/wrong art for ANW civs |
| **GAP: Scoreboard flag rendering** (flag icon as displayed post-game) | **None** | **None** | Post-game screen shows wrong flag |

**Summary:** Static art validation is thorough for file existence and metadata. In-game render fidelity and age-up dialog art have zero automated coverage.

---

### 1.2 Text Content

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| Duplicate locIDs in stringmods.xml producing wrong display name | `validate_no_locid_duplicates.py` — PASS | None | Wellington shows as "Queen Elizabeth" (confirmed 2026-05-08 bug) |
| Unresolved nameID/tooltipID in personality files | `validate_string_resolution.py` — PASS | None | AI slot shows raw ID like `[STR_NAMEID_42]` |
| Leader name in homecity XML doesn't match canonical token map | `validate_homecity_leader_match.py` — PASS | None | "Francis Drake" in Argentine home city (confirmed template residue bug) |
| HTML reference text drifts from mod content | `validate_html_vs_mod.py` — PASS | None | Players read wrong strategy in docs |
| **GAP: In-lobby tooltip text fidelity** (overridden personality name + portrait + tooltip all correct together) | **None** | `validate_live_picker.py` (SKIP — needs game) | Lobby shows "Duke of Wellington" name but Elizabeth portrait |
| **GAP: In-game scoreboard name** (leader name as rendered in-game scoreboard widget) | **None** | **None** | Scoreboard shows generic "British" not "Wellington" |
| **GAP: Leader chat/quote fires correct text** (opening taunt references correct leader) | **None** | `runtime_logs` (SKIP) | "Isabella" quote fires for Dutch civ |
| **GAP: Polish passes — blurb text in picker description panel** | **None** | **None** | Stale or wrong blurb from earlier template shown |

---

### 1.3 AI Dispatch Correctness

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| XS syntax error / undefined symbol stops AI loader | `validate_xs_scripts.py` — PASS | None | AI idles for duration of match |
| Leader doctrine binding wrong (wrong wall_strategy enum wired in leaderCommon.xs) | `validate_ai_behaviour_map.py` — PASS | `validate_doctrine_compliance.py` (SKIP — needs artifact) | Fortress-builder civ never walls; aggressive civ turtles |
| Personality override file doesn't apply at runtime | `validate_personality_active.py` — PASS | None | Base-game AI used instead of ANW doctrine |
| Playstyle modal/spec drift (what spec claims vs what XS dispatches) | `validate_playstyle_modal.py` — PASS | `validate_playstyles.py` (SKIP) | Spec says "rush" but civ booms |
| Probes vs spec mismatch | `validate_probes_vs_spec.py` — PASS | None | Validator reports PASS on wrong data |
| **GAP: Runtime doctrine probes actually firing** (do `[LLP v=2]` probes appear in Age3Log.txt?) | **None** | `validate_runtime_logs.py` (SKIP) | Static validators pass but AI probe machinery silent in live game |
| **GAP: Card shipment sequence matches deck** (AI ships from its registered deck) | None — deck content validated, shipment sequence not | `runtime_logs` (SKIP) | AI ships vanilla British cards from ANW German slot |
| **GAP: Build-order timing invariants** (barracks before min 5, fort before min 15) | **None** | `property_validators_v1.py` (framework exists, no runner) | Civs are strategically non-functional: no army for 20 min |
| **GAP: Unit composition ratios under live game conditions** | **None** | `property_validators_v1.py` (framework exists, no runner) | "Cavalry civ" trains 100% infantry |

---

### 1.4 Game Balance

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| Tech tree reference broken (agetech/treatytech/postindustrialtech resolves to nothing) | `validate_civ_tech_resolution.py` — PASS | None | Civ can never age up |
| Protomods.xml unit reference missing (unit ID in deck doesn't exist in proto) | `validate_protomods.py` — PASS | None | Card shipment produces nothing |
| Homecity card count wrong (not exactly 25) | `validate_homecity_cards.py` — PASS | None | Deck builder shows truncated deck |
| **GAP: Deck card balance** (are any cards game-breakingly strong / free resources infinite loop?) | **None** | **None** | One ANW civ dominates multiplayer; mod gets flagged |
| **GAP: Starting units / pop budget correct for each civ** | **None** | **None** | One civ starts with 0 vills and can never recover |
| **GAP: Age-up politician costs are non-zero** (no free-age exploit) | **None** | **None** | One civ ages up for free; dominant in multiplayer |

---

### 1.5 Scenario Loadability

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| Scenario binary Arxan signature invalid | `validate_scenario_binary.py` — PASS (self-test) | None | Custom scenario rejected by engine |
| Scenario trigger XML malformed | `validate_xml_well_formed.py` — PASS | None | Scenario fails to load |
| **GAP: All 45 ANW civs successfully enter in-game state** (not just lobby) | **None** | `validate_live_picker.py` (SKIP) | 3 civs crash on load (confirmed 2026-05-18 engine instability for ANWGermans, ANWAztecs, ANWArgentines) |
| **GAP: ANW civs work in Empire Wars / Deathmatch / Treaty modes** | **None** | **None** | ANW civ AI idles in Treaty (can't build during timer) |

---

### 1.6 Save/Load Integrity

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| **GAP: Save file roundtrips without data loss** | **None** | **None** | Player saves mid-game, reloads; AI resources reset to 0 or wrong leader |
| **GAP: AI XS state survives save/load** (doctrine knobs re-initialize correctly) | **None** | **None** | AI switches to different playstyle after reload |
| **GAP: String IDs survive save/load** (leader name still resolves after reload) | **None** | **None** | After reload, scoreboard shows raw locID |

---

### 1.7 Multiplayer Determinism

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| **GAP: Replay file bit-perfect roundtrip** (same inputs → same inner hash) | `replay_determinism_validator.py` exists (parser only, no runner) | **None** | Multiplayer desync; players have different game states |
| **GAP: ANW civ AI produces deterministic output across re-runs with same RNG seed** | **None** | **None** | Multiplayer desyncs immediately when any ANW AI is in game |
| **GAP: Host-only vs. both-installed behavior documented** | **None** | **None** | Host uses ANW AI; joiner sees base AI; desync after 30s |

---

### 1.8 Mod Packaging

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| Duplicate locID in packaged mod | `validate_packaged_mod.py` — PASS (warn_is_pass=True) | None | Known dup-locID warning tolerated but not a blocker |
| Orphan XML files (shadow files, .proposed, .bak) | `validate_no_orphan_xml.py` — PASS (warn_is_pass) | None | Dev artifacts shipped to Workshop |
| **GAP: Final .age3mod package contents verified** (every file in manifest exists, no extras) | **None** | **None** | Workshop download missing key files |
| **GAP: Mod loading order vs. base game conflicts** | **None** | `validate_live_mod_install.py` (SKIP) | Mod overrides something it shouldn't; base civ broken |

---

### 1.9 Install Integrity

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| Installed mod files differ from repo | **None** (only live) | `validate_live_mod_install.py` (SKIP) | User has stale files; reports bugs that are already fixed |
| **GAP: Fresh install from Workshop (clean machine test)** | **None** | **None** | .age3mod packaging error; Workshop install silent-fails |
| **GAP: Mod version metadata (modinfo.json / mod.xml) matches release tag** | **None** | **None** | Workshop shows wrong version; player confusion |

---

### 1.10 Technology Unlocks

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| agetech/postindustrialtech/treatytech ref broken | `validate_civ_tech_resolution.py` — PASS | None | Civ cannot advance age |
| Tech prerequisite cycle (tech A requires tech B requires tech A) | Partially: `validate_techtree.py` checks duplicates | **None** | Tech permanently locked; achievement impossible |
| **GAP: Age-up techs cost correct resources** (not 0, not 99999 food) | **None** | **None** | Free age-up exploit; game balance broken |
| **GAP: All 4 age-up politician paths exist** per civ (colonial, fortress, industrial, imperial) | **None** | **None** | "Select Age-Up" dialog shows only 1 politician option |

---

### 1.11 Deck Cards

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| Card ID in homecity doesn't resolve in techtreemods | `validate_homecity_cards.py` — PASS | None | Card appears in deck, produces nothing on ship |
| Deck has != 25 cards | `validate_homecity_cards.py` — PASS | None | Visual truncation in deck builder |
| Card referenced in deck not in decks_anw.json | `validate_homecity_cards.py` — PASS | None | Discrepancy between what AI ships and documented deck |
| **GAP: Card effect actually fires** (shipment triggers correct tech/unit spawn) | **None** | **None** | "Ship 700 Food" card does nothing on shipment |
| **GAP: Cards available per age are gated correctly** (age-1 card not available until colonial) | **None** | **None** | Player gets age-4 card in discovery age |

---

### 1.12 Home City Flow

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| Homecity leader name mismatch | `validate_homecity_leader_match.py` — PASS | None | Wrong hero name visible in home city UI |
| Duplicate home city entries causing double-entry in picker | `validate_no_homecity_doubles.py` — PASS | None | SELECT HOME CITY picker shows base + ANW duplicate |
| Homecity XML parse failure | `validate_xml_well_formed.py` — PASS | None | Crash on home city load |
| **GAP: Home city scene actually renders** (3D model, lighting, camera angle correct) | **None** | Visual capture pipeline (partial — 3/45 civs covered) | Black screen or wrong home city appears in UI |
| **GAP: Home city deck builder shows correct 25 cards** | **None** | **None** | Builder shows 24 or 26 cards; can't customize |
| **GAP: Home city name/blurb text in picker panel** | **None** | **None** | Picker shows "Home City" (generic) not "Tenochtitlan" |

---

### 1.13 Lobby Flow

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| ANW civ not visible in picker | `validate_offline_picker.py` + `validate_offline_matrix.py` — PASS | `validate_live_picker.py` (SKIP) | Player can't select the civ at all |
| Civ picker shows double entry (base + ANW) | `validate_no_homecity_doubles.py` — PASS | None | Two entries for "British"; confusing |
| **GAP: All 45 ANW civs actually selectable in live game** (no crash on select) | **None** | `validate_live_picker.py` (SKIP) | "Germans" crashes lobby on selection |
| **GAP: Personality portrait and name display in AI slot** | **None** | `validate_live_picker.py` (SKIP) | AI slot shows Elizabeth portrait for Wellington |
| **GAP: forcedciv correctly auto-selects civilization** on personality pick | **None** | **None** | Personality dropdown selects "Wellington" but civ stays "British" (wrong token) |

---

### 1.14 End-of-Game Flow

| Failure mode | Static validator | Runtime validator | Launch risk |
|---|---|---|---|
| **GAP: Post-game flag icon renders correctly** | `validate_civmods_art_consistency.py` checks surface key — PASS | **None** | Black or wrong flag on post-game results screen |
| **GAP: Post-game scoreboard shows correct leader name** | **None** | **None** | "Opponent: British AI (Wellington)" shows as "British AI" |
| **GAP: mod.gameover probe fires** (game-over transition doesn't crash XS) | **None** | `validate_runtime_logs.py` (SKIP) | XS exception at game-end triggers error dialog |

---

## 2. New Validator Proposals

### Priority A — High Impact, Low Effort (build before launch)

#### 2.1 `validate_deck_card_effects.py`
- **What it reads:** `data/techtreemods.xml`, `data/decks_anw.json`, `data/homecity*.xml`
- **What it asserts:** Every card ID in every ANW homecity deck has a `<effect>` child in techtreemods (not just a `<tech>` name entry). FAIL if any card tech has an empty effect list. WARN if any effect references a proto unit that isn't in `data/protomods.xml`.
- **Estimated LOC:** ~120
- **Estimated build time:** 2 hours

#### 2.2 `validate_age_up_politicians.py`
- **What it reads:** `data/anwhomecity*.xml` for each civ, `data/techtreemods.xml`
- **What it asserts:** Every ANW homecity has exactly 2–4 valid politician options per age (ages 2–5), each resolving to a `<tech>` entry in techtreemods with a non-zero `<cost>` element. FAIL if any age has 0 options (no age-up path) or all options have 0 cost (free age exploit).
- **Estimated LOC:** ~150
- **Estimated build time:** 2.5 hours

#### 2.3 `validate_mod_version_metadata.py`
- **What it reads:** `modinfo.json`, `mod.xml`, `RELEASE_NOTES_v1.0.md` (parses first version mention)
- **What it asserts:** `modinfo.json` version field matches `mod.xml` version attribute; neither is "0.0.0" or empty; version string follows semver pattern. WARN if RELEASE_NOTES header version doesn't match.
- **Estimated LOC:** ~80
- **Estimated build time:** 1 hour

#### 2.4 `validate_civ_start_state.py`
- **What it reads:** `data/civmods.xml`, `data/protomods.xml`, base game `civ_units.json` if available from extracted bar archives
- **What it asserts:** Every ANW civ has a non-empty starting units list (at least 1 settler/villager variant) in its civ definition. FAIL if any ANW civ's `<startingunit>` resolves to a proto unit that doesn't exist in `data/protomods.xml`.
- **Estimated LOC:** ~130
- **Estimated build time:** 2 hours

#### 2.5 `validate_gameover_probe.py`
- **What it reads:** `game/aiMain.xs` and all civ AI files for the `meta.gameover` probe pattern
- **What it asserts:** The `meta.gameover` probe is registered (i.e., `llProbe("meta.gameover"...)` appears in the XS codebase for every civ or via the shared aiMain). FAIL if the pattern is absent — means game-over events won't fire probes.
- **Estimated LOC:** ~60
- **Estimated build time:** 45 minutes

---

### Priority B — High Impact, Medium Effort

#### 2.6 `validate_save_load_smoke.py`
- **File path:** `tools/validation/validate_save_load_smoke.py`
- **What it reads:** Existing save file artifacts in `artifacts/saves/` (must be pre-captured). If no saves directory exists, the validator SKIPs with a note.
- **What it asserts:** A save file (`*.age3Ysav`) can be l33t-decompressed (same codec as replays); inner payload is non-empty (>1 KB); decompressed size matches declared size in header. A re-loaded save that was captured before and after a 5-minute match should have matching inner hashes when loaded again.
- **Estimated LOC:** ~100
- **Estimated build time:** 3 hours (including save-file capture tooling)

#### 2.7 `validate_tech_prereq_cycles.py`
- **File path:** `tools/validation/validate_tech_prereq_cycles.py`
- **What it reads:** `data/techtreemods.xml`
- **What it asserts:** Builds a directed graph of `<prereq>` relationships across all ANW techs. Runs cycle detection (DFS). FAIL if any cycle exists (A requires B requires A). WARN if any tech has a prereq referencing a tech not in the file (dangling edge to base game).
- **Estimated LOC:** ~140
- **Estimated build time:** 2 hours

#### 2.8 `validate_personality_lobby.py`
- **File path:** `tools/validation/validate_personality_lobby.py`
- **What it reads:** `game/ai/*.personality`, `data/civmods.xml`, `data/stringmods.xml`
- **What it asserts:** For each ANW personality: (a) `<name>` element resolves to a non-empty string in stringmods; (b) `<tooltipid>` resolves similarly; (c) `<forcedciv>` token matches an ANW civ token in civmods.xml; (d) portrait DDT path listed matches a file that passes `validate_ddt_format` checks. This is a tighter static version of the live `validate_live_picker.py`.
- **Estimated LOC:** ~180
- **Estimated build time:** 3 hours

#### 2.9 `validate_blurb_coverage.py`
- **File path:** `tools/validation/validate_blurb_coverage.py`
- **What it reads:** `data/anw_civ_blurbs.json`, `data/civmods.xml` (ANW token list)
- **What it asserts:** Every ANW civ token has a non-empty entry in `anw_civ_blurbs.json`. Blurb length >= 40 chars (not a stub). No blurb contains template placeholder text like "PLACEHOLDER" or "TBD" or duplicates another civ's blurb verbatim (text-content drift detector).
- **Estimated LOC:** ~90
- **Estimated build time:** 1.5 hours

#### 2.10 `validate_packaged_mod_contents.py`
- **File path:** `tools/validation/validate_packaged_mod_contents.py`
- **What it reads:** The final `.age3mod` package file (zip-based). If absent, SKIPs.
- **What it asserts:** Lists all files in the archive; verifies every file path in the manifest resolves to an actual zip entry; verifies no stale `.proposed`, `.bak`, or `_dev` suffix files were included; verifies `modinfo.json` is present with correct version.
- **Estimated LOC:** ~120
- **Estimated build time:** 2 hours

---

### Priority C — Medium Impact, Higher Effort

#### 2.11 `validate_empire_wars_ai.py`
- **File path:** `tools/validation/validate_empire_wars_ai.py`
- **What it reads:** `game/ai/aiHeader.xs`, per-civ XS files, `game/aiMain.xs`
- **What it asserts:** Each ANW civ's XS boot path handles the `gIsEmpireWars` flag (or equivalent mode variable). FAIL if no reference to empire wars / treaty flags exists in any ANW civ's ai file (means the civ treats every game as standard Supremacy).
- **Estimated LOC:** ~100
- **Estimated build time:** 2 hours

#### 2.12 `validate_localization_coverage.py`
- **File path:** `tools/validation/validate_localization_coverage.py`
- **What it reads:** `data/stringmods.xml` (English), optionally `data/stringmods_*.xml` for other locales
- **What it asserts:** Every `_locID` that appears in ANW civ/personality/homecity XML files is present in all locale string files (not just English). WARN for missing translations with a count. This is the gap the RELEASE_QA_PLAN flagged under "Tier 4 - Polish / localization".
- **Estimated LOC:** ~130
- **Estimated build time:** 2.5 hours

---

## 3. Live-Game Validators with Non-Intrusive Capture

### Design constraints
- **Forbidden:** kwin, Claude_Preview, Claude_in_Chrome (cursor-grabbing tools)
- **Allowed:** `gamescopectl screenshot` (passive pixel read, no mouse movement) — see `tools/aoe3_automation/lobby_driver.py:292` for working implementation
- **Allowed:** `pytesseract` OCR on captured frames — see `tools/validation/ocr_validator.py`

### 3.1 Proposed Runtime Validation Framework: `tools/validation/validate_runtime_passive.py`

The framework operates in three stages:

**Stage 1 — Passive screenshot capture loop**

```python
# Pseudocode — actual impl uses lobby_driver.screenshot()
def passive_capture_loop(interval_s=30, duration_s=600, out_dir=Path("artifacts/runtime_caps")):
    """Capture one screenshot every `interval_s` for `duration_s` seconds.
    Never moves the mouse. Uses gamescopectl screenshot exclusively."""
    t0 = time.monotonic()
    i = 0
    while time.monotonic() - t0 < duration_s:
        out = out_dir / f"cap_{i:04d}.png"
        lobby_driver.screenshot(out)  # existing gamescopectl wrapper
        time.sleep(interval_s)
        i += 1
```

**Stage 2 — OCR extraction + structured metrics**

Each captured frame goes through `ocr_validator.OCRValidator.validate_screenshot()`. Additionally, a pixel-region probe reads the HUD resource bar at fixed coordinates (y≈20 for 1920x1080) to detect whether we're in-game vs on loading screens:

```python
RESOURCE_BAR_Y = 20          # top of resource HUD band
IN_GAME_ANCHOR_PIXEL = (50, 20)   # food icon area — non-zero in-game, black on menu
```

**Stage 3 — State sequence assertions**

The `PassiveRuntimeValidator` runs the following assertions over the captured sequence:

| Assertion | Method | PASS condition |
|---|---|---|
| `age_progression` | OCR for "Colonial"/"Fortress"/"Industrial"/"Imperial" in screen text | At least one age-up text appears before t=15min |
| `no_xserror_dialog` | OCR scan for "XS Script Error" / "Assertion failed" anywhere on screen | Zero matches in any frame |
| `ai_active` | Pixel brightness change between frames 2 and N (>5% of pixels change) | Mean frame-delta > threshold (proves AI is moving units, not frozen) |
| `leader_name_present` | OCR for known leader name strings in HUD region | At least one leader name appears in scoreboard strip |
| `no_crash_banner` | OCR for "The application has unexpectedly quit" | Zero matches in any frame |
| `hud_present` | Pixel row probe at y=20 non-black | HUD resource bar visible (proves we reached in-game state) |

**Integration into run_all_validators.py:**

Add a new `ValidatorSpec` with `needs_game=True, slow=True`:

```python
ValidatorSpec("runtime_passive",
              "tools/validation/validate_runtime_passive.py",
              args=["--duration", "600", "--civ", "ANWBritish"],
              needs_game=True, slow=True, timeout_s=700)
```

**Estimated LOC:** ~300  
**Estimated build time:** 6 hours  

---

### 3.2 Per-civ lobby screenshot assertion: `validate_lobby_screenshots.py`

Extends `validate_live_picker.py` (already exists with `--ocr` flag) with non-intrusive passive assertions:

1. `gamescopectl screenshot` is called once per civ slot change (user must navigate game to the target state; no automation of clicks)
2. OCR extracts text from the personality name region (top-left of AI slot, ~y=300-380)
3. Asserts extracted name matches expected leader name from `anw_token_map`

This reuses the existing `lobby_driver.screenshot()` + `ocr_validator.OCRValidator` pipeline without any cursor movement.

---

## 4. Replay-Based Determinism Testing

### 4.1 Feasibility Assessment

AoE3 records `.age3Yrec` replay files using the l33t wrapper (confirmed in `replay_determinism_validator.py` — `is_l33t()` codec already working). The inner payload is compressed proprietary binary. Key finding from code review:

- **Hash-based determinism checking is already implemented** in `DeterminismValidator.compare_replays()` — it compares `inner_hash` (SHA256 of decompressed payload) between two replay files
- **RNG seed extraction is NOT yet implemented** (`extract_rng_seed()` returns None — inner format not reverse-engineered)
- **Consequence:** We can check "did two replays of the exact same match produce identical bytes?" but we cannot force a replay to re-run with the same seed from Python

### 4.2 What Determinism Testing Can and Cannot Do

**Can do (today):**
- Record replay A, record replay B of the same match played identically (same map/civ/seed via replay-watch mode if AoE3 supports it), compare `inner_hash`
- Batch validate that all stored replay files are structurally valid (correct l33t magic, non-corrupted zlib stream)
- Alert if a replay file is corrupted or truncated (integrity gate)

**Cannot do (blocked by unknown inner format):**
- Re-run a replay programmatically and check output determinism without human involvement
- Extract RNG seed to parameterize property-based test runs
- Field-decode the replay to extract per-frame unit positions or AI decisions

**Recommendation:** Treat replays as regression snapshots only. Bit-perfect inner_hash comparison is the gate. If a mod change causes inner_hash drift on a stored reference replay, that's evidence of changed behavior.

### 4.3 Replay Capture Protocol

```
artifacts/
  replays/
    reference/
      ANWBritish_supremacy_8p_seed42.age3Yrec      # 5-min reference run
      ANWFrench_supremacy_8p_seed42.age3Yrec
      ... (one per civ)
    regression/
      <run_date>/
        ANWBritish_supremacy_8p_seed42.age3Yrec    # re-run after code change
```

**Capture steps per civ (manual, one-time baseline):**
1. Start skirmish: 1v7 AI, standard map, 8 players, `--seed 42` (if AoE3 supports seed parameter, else use fixed map)
2. Let run for exactly 5 minutes (no user input after start)
3. Quit to main menu — AoE3 saves replay automatically to `~/Games/Age of Empires 3 DE/<id>/savegame/`
4. Copy to `artifacts/replays/reference/<civ>_supremacy_8p.age3Yrec`

**Replay file size estimates:**

| Match length | Typical compressed size | Decompressed |
|---|---|---|
| 5-minute skirmish | ~300–800 KB | ~3–8 MB |
| 10-minute skirmish | ~600–1500 KB | ~6–15 MB |
| 20-minute skirmish | ~1–3 MB | ~10–30 MB |

**For 45 civs × 5-min skirmish:** approximately 45 × 600 KB = ~27 MB compressed. Fits comfortably in git LFS without cost concerns.

### 4.4 Git LFS Storage Recommendation

```bash
# .gitattributes addition
*.age3Yrec filter=lfs diff=lfs merge=lfs -text
artifacts/replays/ filter=lfs diff=lfs merge=lfs -text
```

LFS tracking for `*.age3Yrec` keeps main repo history clean while storing binary blobs efficiently. At ~27 MB baseline + ~27 MB per regression run, this is sustainable.

### 4.5 Regression Gate: `validate_replay_regression.py`

Proposed validator (extends existing `replay_determinism_validator.py`):

- **Input:** `artifacts/replays/reference/` + `artifacts/replays/regression/<date>/`
- **For each civ:** load reference replay, load regression replay, compare `inner_hash`
- **PASS:** all inner hashes match reference
- **FAIL:** any inner hash differs — output which civs drifted
- **SKIP:** no regression directory exists (first run establishes baseline)

**Estimated LOC:** ~120 (leverages existing `DeterminismValidator`)  
**Estimated build time:** 3 hours (includes LFS setup + capture protocol doc)

---

## 5. Property-Based Testing

### 5.1 Proposed Invariants per Civ

Each civ should satisfy the following invariants in a 12-minute standard skirmish:

| Invariant ID | Invariant | Evidence source |
|---|---|---|
| `INV_AGE2` | Civ reaches at least Age 2 (Colonial) by t=12:00 | `[LLP v=2] posture.snapshot.age >= 2` in Age3Log.txt |
| `INV_ARMY` | At least 10 military units at t=12:00 | `[LLP v=2] comp.snapshot.total_military >= 10` |
| `INV_BOOT` | AI loader bootstrap fires within 30s of game start | `meta.boot` probe appears before t=30000ms |
| `INV_NO_IDLE` | AI is not idle (0 units, 0 buildings) at any snapshot | `comp.snapshot.total_military + total_buildings > 0` at all snapshots |
| `INV_CARD_DECK` | All shipped cards are from the registered deck | `compliance.ship.card` probes only reference `decks_anw.json[civ]` entries |
| `INV_WALL_STRAT` | Wall strategy enum matches spec | `meta.boot.wallStrategy == playstyle_spec[civ].claims.wall_strategy` |
| `INV_PROBE_DENSITY` | At least 1 probe per 60 seconds of game time | `len([LLP v=2] lines) / game_duration_s >= (1/60)` |

### 5.2 Property-Based Runner Architecture

**File:** `tools/validation/validate_property_overnight.py`

```python
# High-level structure
class PropertyOvernightRunner:
    def __init__(self, civs, seeds, runs_per_civ=5):
        self.civs = civs           # list of ANW civ tokens
        self.seeds = seeds         # list of RNG seeds (or None = random)
        self.runs_per_civ = runs_per_civ
    
    def run_one(self, civ, seed):
        """Launch match, wait for Age3Log, extract probes, check invariants."""
        # 1. Launch AoE3 in game-mode skirmish (via manage_game.py or equivalent)
        # 2. Wait for Age3Log to contain meta.gameover probe (up to 15 min timeout)
        # 3. Parse log via parse_match_log.py
        # 4. Run PropertyValidatorSuite.validate(log_content, {civ context})
        # 5. Return pass/fail per invariant
    
    def run_all(self):
        """Iterate over all civs × seeds. Write report."""
        results = {}
        for civ in self.civs:
            for seed in self.seeds:
                results[(civ, seed)] = self.run_one(civ, seed)
        return results
```

The runner depends on the AI probe infrastructure (`[LLP v=2]` probes in Age3Log.txt) which is already implemented in `property_validators_v1.py` + `parse_match_log.py`.

### 5.3 Overnight Run Configuration

Recommended parameters for a pre-launch overnight run:

```bash
python3 tools/validation/validate_property_overnight.py \
    --civs all \
    --seeds 1 2 3 4 5 \
    --runs-per-civ 5 \
    --match-duration 720 \
    --report artifacts/validation/property_overnight_report.html
```

- 45 civs × 5 seeds × ~15 min per match = **~56 hours** (too long for one night)
- **Practical overnight target:** 45 civs × 2 seeds × 12 min = ~18 hours. Launch Friday evening, review Saturday morning.
- Flag: any civ failing `INV_BOOT` or `INV_AGE2` on both seeds is a hard blocker for v1.0.

### 5.4 Known blocker: Engine stability ceiling

As documented in `project_anw_visual_capture_ceiling.md`, at least 3 civs crash mid-skirmish (ANWGermans, ANWAztecs, ANWArgentines). Property-based testing will expose more such civs. Each crash counts as `INV_BOOT` failure. **Resolving engine-crash civs before the overnight run is a prerequisite.**

Suspected root causes (from memory file): `data/anwhomecity<civ>.xml` loading issues, or per-civ `game/ai/civs/<civ>/` overrides causing XS exception before the loader fires.

---

## 6. Prioritization by Impact/Effort Ratio

The following table ranks all proposed validators. Impact is rated 1–5 (5 = launch-blocking if missed); effort is rated 1–5 (1 = easiest).

| Rank | Validator | Impact | Effort | I/E | Why |
|---|---|---|---|---|---|
| **1** | `validate_age_up_politicians.py` | 5 | 1 | **5.0** | Zero-cost age-up exploit or missing politicians = game-breaking; build is cheap static XML check |
| **2** | `validate_personality_lobby.py` | 5 | 2 | **2.5** | Lobby personality display is the first thing every player sees; static check covers most cases without needing game running |
| **3** | `validate_deck_card_effects.py` | 4 | 1 | **4.0** | Shipped cards that do nothing are a high-visibility bug; techtreemods already parsed elsewhere |
| **4** | `validate_blurb_coverage.py` | 3 | 1 | **3.0** | Text-content drift is a known repeat offender; very cheap to write |
| **5** | `validate_mod_version_metadata.py` | 4 | 1 | **4.0** | Wrong version number on Workshop submission causes player confusion and makes changelogs misleading; trivial to implement |
| 6 | `validate_civ_start_state.py` | 4 | 2 | 2.0 | Starting with 0 villagers is catastrophic; medium effort |
| 7 | `validate_tech_prereq_cycles.py` | 3 | 2 | 1.5 | Graph cycle detection; medium risk |
| 8 | `validate_gameover_probe.py` | 3 | 1 | 3.0 | Simple grep; catches XS error at game-end |
| 9 | `validate_replay_regression.py` | 4 | 3 | 1.3 | Determinism catch; high effort because requires capturing baseline replays |
| 10 | `validate_runtime_passive.py` | 5 | 4 | 1.25 | Most comprehensive coverage but needs live game + build time |
| 11 | `validate_save_load_smoke.py` | 4 | 3 | 1.3 | Save/load is completely untested; medium-high effort |
| 12 | `validate_packaged_mod_contents.py` | 3 | 2 | 1.5 | Workshop packaging correctness |
| 13 | `validate_property_overnight.py` | 5 | 5 | 1.0 | Maximum coverage but multi-hour runtime; post-launch monitoring tool |
| 14 | `validate_empire_wars_ai.py` | 2 | 2 | 1.0 | Niche game mode; acceptable to leave for post-v1.0 |
| 15 | `validate_localization_coverage.py` | 2 | 3 | 0.67 | English-only v1.0 is documented; low urgency |

---

## 7. Top 5 Validators to Build Before Launch

In order of construction priority:

### #1 `validate_age_up_politicians.py`
**Why first:** A civ that cannot age up or can age up for free is a game-breaking exploit. This is a pure static XML check of homecity files and techtreemods — no game required. Build time: 2.5 hours.

**Acceptance test:** Run against all 45 ANW homecity XMLs. Zero FAIL on politician costs (must be > 0 food/gold/XP equivalent). Zero FAIL on politician count (must be >= 2 per age transition).

### #2 `validate_deck_card_effects.py`
**Why second:** A card that ships but does nothing is a high-visibility user complaint. The data is already parsed by `validate_homecity_cards.py`; this validator just adds the `<effect>` existence check on top. Build time: 2 hours.

**Acceptance test:** Every card in `data/decks_anw.json` has at least one `<effect>` child in techtreemods. Zero FAILs.

### #3 `validate_mod_version_metadata.py`
**Why third:** Must be correct before Workshop submission — cannot patch version metadata after upload without a new submission. Trivial to write, high consequence if missed. Build time: 1 hour.

**Acceptance test:** `modinfo.json` version matches `mod.xml` version; both match the v1.0 tag in RELEASE_NOTES.

### #4 `validate_personality_lobby.py`
**Why fourth:** The personality matrix is the single most-visible dynamic feature of the mod (overridden names, portraits, tooltips, forcedciv). A static pre-flight check that all 45 personalities have consistent name/portrait/civ triples reduces the mandatory live-game testing burden significantly. Build time: 3 hours.

**Acceptance test:** All 45 ANW personality entries pass: name resolves in stringmods, tooltipid resolves, forcedciv exists in civmods, portrait DDT has correct format byte. Zero FAILs.

### #5 `validate_blurb_coverage.py`
**Why fifth:** Text-content drift between sources has been a repeat offender (Polish passes 3-7 finding it). A 1.5-hour validator that catches stale blurbs, template placeholders, and duplicate text prevents last-minute scramble. Build time: 1.5 hours.

**Acceptance test:** All 45 ANW civ tokens have blurb entries >= 40 chars with no placeholder text. Zero FAILs.

---

## 8. Current Coverage Summary

| Category | Static coverage | Runtime coverage | Gap severity |
|---|---|---|---|
| Visual art (file, format, consistency) | STRONG (6 validators) | Partial (3/45 visual captures) | Medium — render fidelity unvalidated |
| Text content | STRONG (4 validators) | WEAK (live_picker SKIP) | High — lobby text never automated |
| AI dispatch | STRONG (6 validators) | SKIP (needs artifact) | High — runtime probe behavior unconfirmed |
| Game balance | MEDIUM (tech/proto checked) | None | High — card effects, age-up costs unchecked |
| Scenario loadability | MEDIUM | SKIP | High — 3 civs known to crash |
| Save/Load integrity | None | None | High — never tested |
| Multiplayer determinism | None | None | Medium — LAN/MP not common use case for mods |
| Mod packaging | MEDIUM | None | Medium — contents not verified |
| Install integrity | None | SKIP | High — fresh install never automated |
| Tech unlocks | STRONG (civ_tech_resolution) | None | Medium — costs/prereqs unchecked |
| Deck cards | STRONG (homecity_cards) | None | High — card effects unvalidated |
| Home city flow | STRONG (4 validators) | Partial (3/45) | Medium — scene render unvalidated |
| Lobby flow | STRONG (offline_picker) | SKIP | High — live picker never run |
| End-of-game flow | WEAK (art surface only) | None | Medium |

**Overall honest coverage estimate: 85% static / 25% runtime**

Closing the top-5 pre-launch validators brings static coverage to ~92%. Running `validate_live_picker.py` and `validate_runtime_passive.py` on a representative subset of civs (British, French, Inca as known-stable; one crash-prone civ after debugging) brings effective coverage to ~95%. Full 100% requires resolving the engine-crash blockers for ANWGermans/ANWAztecs/ANWArgentines and running the overnight property suite.

---

## 9. Resolving the 7 SKIPs

The 7 current SKIPs in `run_all_validators.py` all require `--include-live` or `--include-runtime`. Recommended actions:

| Validator | Unblock strategy |
|---|---|
| `playstyles` | Run once per major XS change with `--include-runtime` pointing to a captured Age3Log artifact |
| `doctrine_compliance` | Same as above — needs live Age3Log |
| `visuals` | Capture 3 stable civs (British, French, Inca) with visual capture pipeline; store in `artifacts/validation/visual_art_v2/`; run with `--include-runtime` |
| `live_mod_install` | Run manually before each Workshop submission with game running |
| `runtime_logs` | Run with `--include-live` as part of the pre-launch weekend session |
| `live_picker` | Run with `--include-live`; add `--ocr` flag; confirm 45 ANW civs visible and selectable |
| `input_harness` | Run once to verify at least one input backend works; gate is already automated |

**Unblocking `live_picker` + `runtime_logs` in a single pre-launch game session would move the gate from 42/49 PASS to 48/49 PASS**, with only `visuals` (art capture) remaining as the last known gap.

---

*End of TEST_COVERAGE_PLAN.md — 2026-05-26*
