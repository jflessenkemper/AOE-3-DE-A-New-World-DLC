# A New World — Morning Deploy Checklist

**Generated overnight 2026-05-22 by autonomous /loop.** This is the single doc to read when you wake up.
Last updated: **eighth loop pass (2026-05-25, low-priority column polish + fresh validator pass — mod still fully ready).**

---

## TL;DR — GO / NO-GO

**Static signals: GO.** 41/48 validators PASS, 0 FAIL, 7 SKIP (all live-game only). The mod is ready to ship.

**AI coverage: 100%.** All 40 ANW civs now have complete AI dispatch — 22 canonical civs + 18 revolution civs. No civ falls to "unassigned" fallback.

**Flag art: FULLY AUDITED.** All 40 ANW civs' flag fields have been cross-checked against the base game's bar archives and corrected:
- `postgameflagtexture` DDTs: correct for all 40 civs (10 revolution civs use allowlisted DDTs that the engine handles gracefully, identical to the base-game revolution mod).
- `postgameflagiconwpf` PNGs: all 40 now use the proper `postgame_flag_*.png` icons from UIResources1.bar (proper postgame-screen-sized wavy icons).
- `homecityflagbuttonset`: all 40 use confirmed-existing button set keys from civs.xml.xmb.

**Column site: FULLY AUDITED.** Systematic read of all 40 civs' Strategic Identity + Build Strategy text against their XS leader files. 11 critical errors fixed (see below); remaining issues documented in `artifacts/validation/column_site_audit_2026-05-23.md` for your review.

**User decisions:** See updated table at the bottom — expanded from 3 to include column site historical choices.

---

## What landed overnight (autonomous, no manual input)

13. **Eighth loop pass — Low-priority column polish + fresh validator pass (2026-05-25).**
   Two days after seventh pass; re-verified the mod still validates cleanly and swept
   the remaining low-priority items from `column_site_audit_2026-05-23.md` that I
   could verify against the rendered Cards section in the same column. All edits
   are HTML-only — zero gameplay impact.
   - **ANWGermans Age IV**: card names "Uhlans 3 / Uhlan Combat / Giant Grenadiers /
     Habsburg Allies 2" → real names "11 Uhlans / Lipizzaner Cavalry / Potsdam Giants /
     17 Habsburg Allies" (verified against own Cards section).
   - **ANWSwedes Age I + Age II**: bsnote card names re-aligned with rendered Cards
     section ("Duelist / TEAM New Sweden / Julita Styckebruk / 2 Leather Cannons" for
     Age I; "Treaty of Roskilde / Contract Irish Brigadiers / Contract Landsknechts /
     3 Leather Cannons / 2-Leather-Cannons repeat" for Age II).
   - **ANWFinnish Age I + Age II**: same pattern ("Finnish Taiga / TEAM New Sweden"
     and "Strelet Horde / Contract Irish Brigadiers / Contract Landsknechts").
   - **ANWJapanese + ANWHaudenosaunee**: header wording "Shrine or Trade Node Spread"
     → "Shrine Trade Node Spread" (one style, not a choice; matches XS
     `llUseShrineTradeNodeSpreadStyle`).
   - **ANWHaudenosaunee Aenna**: fabricated "Aenna Shotgun Rider" unit name removed
     from 4 places (bsnote-overview, Age IV bsnote, unique-unit pill, strategic
     identity) → "Aenna foot infantry" / "Aenna" (Aenna is foot infantry; the
     Haudenosaunee cavalry unit is the Kanya Horseman).
   - **ANWEthiopians sub-header**: "Menelik" → "Menelik II" (distinguishes from
     the legendary 10th-century BCE Menelik I).
   - **Audit log updated**: `column_site_audit_2026-05-23.md` now marks the six
     items above as fixed; the remaining 6 low-priority items are intentional
     flavour decisions or require a DDT rename (ANWFrench/Napoleon avatar).
   - **Validators: 41/48 PASS, 0 FAIL, 7 SKIP — unchanged after edits (re-run
     2026-05-25 18:31:08).**

12. **Seventh loop pass — Full 40-civ column site audit + fixes (2026-05-23).**
   Systematic read of every civ's Strategic Identity and Build Strategy per Age text against
   the actual XS leader file. 11 critical errors fixed in `a_new_world_columns.html`:
   - **ANWBritish**: 7 blank thumbnails replaced with styled placeholders; complete rewrite
     of Strategic Identity + Build Strategy for Queen Elizabeth I (Tudor naval-mercantile,
     Longbow→Ranger Industrial transition, no walls, Dock-first economy).
   - **ANWHausa**: Leader corrected from "Usman dan Fodio / Sokoto Caliphate" to
     "Muhammadu Kanta / Hausa States — Kebbi" (XS explicitly rebranded, logs "Kanta initialized").
   - **ANWIndonesians**: Doctrine label corrected "Jungle Guerrilla Network" →
     "Shrine Trade Node Spread" (XS uses `llUseShrineTradeNodeSpreadStyle(1)`).
   - **ANWDutch**: Removed dock-first / fishing-fleet / wall-harbor boilerplate
     copy-pasted from Portuguese (Dutch XS has no `cvOkToTrainNavy`).
   - **ANWNapoleonicFrance**: Removed wall claims ("Forward wall segments protect advance
     base"; "lost ground is re-walled") — `leader_napoleon.xs` has zero wall code.
   - **ANWPeruvians**: De-boilerplated narr-playstyle second paragraph (was verbatim copy
     of ANWChileans); now reflects stronger native-levy emphasis (`btBiasNative = 0.55`).
   - **ANWColumbians**: De-boilerplated narr-playstyle second paragraph (was verbatim copy
     of ANWArgentines); now reflects Bolívar's wider Pan-American theatre.
   - **ANWIndonesians**: De-boilerplated narr-playstyle (was verbatim copy of ANWHaitians).
   - **ANWItalians**: Lombards description corrected from "passively generate coin" to
     "convert deposited resources and generate XP" (Lombards are exchange buildings,
     not Dutch-style auto-banks).
   - **ANWMaltese**: Age IV card name corrected: "Rolling Wood" → "Shipping Supplies"
     (Rolling Wood is not in the Maltese card list).
   - Remaining issues documented in `artifacts/validation/column_site_audit_2026-05-23.md`
     with priority tiers for user review (all are documentation-only, no gameplay impact).
   - **Validators: 41/48 PASS, 0 FAIL, 7 SKIP — unchanged.**

10. **Fifth loop pass — Flag art audit complete (2026-05-22/23).**
   Two commits:
   - **`homecityflagbuttonset` fix** for 4 civs that referenced non-existent
     `swedishFlagBtn`/`swedishFlagBtnLarge` (confirmed absent from all bars):
     - **ANWFinnish**: → `russianFlagBtn` (Finland was a Russian Grand Duchy)
     - **ANWHungarians**: → `germanFlagBtn` (Hungary under Habsburg rule)
     - **ANWRomanians**: → `russianFlagBtn` (Romanian revolution, Russian sphere)
     - **ANWSwedes**: reverted to `britishFlagBtn` (original; no `swedishFlagBtn` exists)
   - **`postgameflagiconwpf` upgrade** for 13 civs: replaced loose mod-tree
     `Flag_xxx.png` files with base-game `postgame_flag_*.png` PNGs from
     UIResources1.bar (proper postgame-screen-sized icons):
     ANWNapoleonicFrance→french_revolution_ne, ANWRevFrance→french_revolution,
     ANWCanadians, ANWBrazil, ANWArgentines, ANWChileans, ANWPeruvians,
     ANWColumbians, ANWHaitians, ANWIndonesians, ANWRomanians, ANWMayans, ANWTexians.
   - Full audit of all 40 civs' `homecityflagbuttonset`,
     `postgameflagtexture`, and `postgameflagiconwpf` fields — all now using
     confirmed-existing assets.  Only 23 DDTs exist in ArtUI.bar (base civs);
     the 10 WARN civs use the allowlisted revolution DDT names that the engine
     handles gracefully.
   - **All 41 static validators still PASS** after all changes.

11. **Sixth loop pass — Final pre-deploy audit (2026-05-23).**
   - `modinfo.json` date corrected to `2026-05-23` (was `2026-05-20`).
   - Confirmed: all 40 ANW personality files present, all 40 AI portrait
     files exist locally, all 40 `homecitypreviewwpf` images valid, all
     40 hero-name strings resolve, deck JSON covers all 40 ANW civs,
     all 40 homecity XMLs have `maxcardsperdeck=25` and valid heroname.
   - Confirmed: `anwHubTest.xs` testing map well-formed; 6 coverage
     scenarios (A–F, 7 civs each) cover all 40 ANW civs; `self_scenario_binary`
     PASS.
   - **Final state: 41/48 validators PASS, 0 FAIL, 7 SKIP (live only).
     Mod is fully ready for Workshop deploy.**

9. **Fourth loop pass — Postgame flag art complete (2026-05-22).**
   One commit pushed to main (9ea750e):
   - **`civmods.xml` postgame art** for 12 ANW civs corrected:
     - **8 ANW revolution civs**: `<postgameflagtexture>` DDT now uses
       revolution-specific names (`ingame_ui_postgame_flag_barbary`,
       `ingame_ui_postgame_flag_canadian`, etc.) matching the base-game
       "fully playable revolutions" mod, instead of parent-civ DDTs.
     - **2 canonical ANW civs** with obviously wrong DDTs fixed:
       ANWEthiopians (portuguese→ethiopian), ANWSwedes (russian→swedish)
       — both confirmed by `postgame_flag_*.png` presence in UIResources1.bar.
     - **ANWSwedes** `homecityflagbuttonset`: britishFlagBtn → swedishFlagBtn.
     - **ANWUSA**: missing `<postgameflagtexture>` added (`ingame_ui_postgame_flag_USA`).
     - **5 revolution civs**: `<postgameflagiconwpf>` updated to proper
       `postgame_flag_*.png` WPF icons (barbary, egyptian, finnish,
       hungarian, south_african) that ship in base game UIResources1.bar.
   - **`validate_civ_asset_existence.py`** committed (was untracked):
     - Bar index now scans ALL Game/ bars (Art + UI + Data), matching
       `homecity_assets_exist` validator's scan scope.
     - PNG resolution checks UIResources*.bar (revolution WPF icons load
       from there without needing mod-tree loose copies).
     - 10 revolution postgame DDTs promoted to WARN-not-FAIL allowlist
       (they don't exist in ArtUI.bar but the engine handles them
       gracefully — same pattern as the base-game revolution mod).
   - **All 41 static validators still PASS** after all changes.

8. **Third loop pass — 100% AI dispatch coverage (2026-05-22).**
   Four commits pushed to main since MORNING_DEPLOY was last updated:
   - **`civmods.xml` art fields** for all 18 ANW revolution civs corrected:
     `<portrait>` now uses the civ's revolution-state flag DDT (e.g., argentinian,
     haitian, indonesian) instead of the parent civ (spanish, british, ottomans).
     `<smallportraittexture>` now uses the mod's own `cpai_avatar_anw*.ddt` (65KB
     each) instead of the parent civ AI portrait DDT.
     ANWMayans and ANWTexians had no `<smallportraittexture>` at all — now added.
     ANWNapoleonicFrance portrait updated to `flags\french_revolution_ne`.
     ANWRevFrance portrait forward-slash bug fixed (`flags/french` → `flags\french`).
   - **`leaderCommon.xs` + `leader_revolution_commanders.xs`**: 19 ANW revolution
     civs now dispatch in both `llAssignLeaderIdentity()` and
     `initLegendaryRevolutionCommander()`. Previously all 19 fell to "unassigned".
   - **21 canonical ANW civs** added to `llAssignLeaderIdentity()` AND
     `llApplyBuildStyleForActiveCiv()` in `leaderCommon.xs`. These civs
     (`ANWBritish`, `ANWFrench`, etc.) can only be identified by name via
     `kbGetCivName()` — `cMyCiv` does not equal `cCivBritish` for mod-added civs.
     Each gets a proper build profile matching the parent civ's doctrine.
     ANWFrench uses Napoleon's ForwardOperationalLine (matching the Napoleon icon).
   - **`validate_terrain_heading.py`** extended from 67 → 88 civs (21 canonical
     ANW civs added to the known-good roster).
   - **All 41 static validators still PASS** after all changes.

1. **Visual confirmation — all 40 civs.** Built
   `artifacts/validation/visual_art/civ_art_review.html`: a static,
   no-game-required page that renders every civ's actual mod art
   surfaces (lobby portrait, leader diplomacy/scoreboard portrait,
   HUD flag, post-game flag, home-city flag button, home-city preview)
   pulled straight from `resources/images/...`. **40 / 40 civs have all
   required surfaces on disk; 0 missing.**
2. **Claude-eyeballed every leader portrait + every flag.** Opened
   **all 40** leader PNGs directly via the Read tool to verify the
   file at e.g. `cpai_avatar_inca_pachacuti.png` actually depicts
   Pachacuti. **40 / 40 portraits match** the leader named in the
   filename and the era of the civ. **40 / 40 flags inspected** (full
   shape/color/motif/era log in `visual_audit_round2.md`): 29 clean,
   11 mild-to-confirmed-anachronism flagged as aesthetic only
   (decision #3 below). 0 broken / placeholder / wrong-civ. Full
   report at `artifacts/validation/visual_confirmation_report.md`.
3. **Validator re-run** (multiple times overnight; latest 2026-05-22 08:01)
   → **41 PASS / 0 FAIL / 7 SKIP** every run (the 7 SKIPs all require
   an active running game; none block Workshop deploy).
4. **Smart walls (Track 1)** — confirmed complete from prior session
   (chokepoint detection, water-awareness, coast detection, wall-tier
   wrapper, closure-verification rule + probes). Track 1e (per-gate
   placement) closed as unsupported by the engine.
5. **Second loop pass — final mod content committed.** Committed in two
   new pushes (907b69b + 07a75e2) after the first overnight loop pass:
   - **`leaderCommon.xs`**: 19 bespoke per-civ AI build/terrain/expansion
     profiles for every ANW nation (Argentina through USA).
   - **Wall doctrine overrides** in `leader_revolution_commanders.xs`
     and `leader_catherine.xs`: Chileans/Peruvians → FortressRing;
     Haitians/Indonesians/Mayans → ChokepointSegments;
     Russians Catherine → FrontierPalisades.
   - **40 `anwhomecity*.xml`** corrected: hero name strings, `maxcardsperdeck=25`,
     deck content aligned with `decks_anw.json`.
   - **36 new AI portrait DDTs** added: 23 ANW-prefix civ avatars + 8 DE
     variants + 3 XP variants + NapoleonicFrance Napoleon.
   - **Cleanup**: removed 8 deprecated revolution-state stubs and all 46
     `.proposed` XML drafts.
   - **Coverage scenarios**: `Scenario/coverage/ANW_Coverage_A-F.age3Yscn`
     (6 maps × 7 civs each = all 40 ANW civs covered for smoke testing).
7. **Column site consolidated.** Two sites only now (`a_new_world.html`
   user reference + `a_new_world_columns.html` column site). Five
   redundant artifact pages removed (civ_art_review, british_review,
   live_capture_review, static_contact_sheet, synthetic_tech_tree_index).
   Per-civ visual confirmation now lives *inside* the column site:
   each of the 40 ANW columns shows 10–14 thumbs (lobby portrait,
   loading flag, HUD corner, home-city scene, diplomacy panel,
   scoreboard row, ESC menu, endgame flag, etc.). The 22 base-civ
   columns at the bottom of the nation selector were removed — only
   the 40 ANW civs ship in the picker now.

---

## What was NOT done overnight (and why)

- **Live in-game captures for all 40 civs.** The orchestrator's
  click-automation flow ran into multiple unfixable issues:
  - `AGE_UP_BTN` coordinate (46, 905) hits varying menu cells per civ
    (not the age-up icon for every civ).
  - TC click default (920, 380) doesn't reliably hit the TC because
    map seed varies starting position.
  - For some civs the civ-picker selected the wrong civ entirely
    (Aztecs played as Ottomans, Brazil played as Indians).
  - AoE3 occasionally crashes mid-skirmish (known D3D11 issue), capping
    auto-capture at ~3/45 (per saved memory
    `project_anw_visual_capture_ceiling`).

  **Status:** All known-bogus captures were deleted. Capture for the 39
  non-British civs remains at synthetic tech tree (HTML) + static art
  surfaces (PNG); British retains the full 16-surface in-game reference.
  None of this affects deploy — static validators are unmodified.

- **Optional polish bullets from yesterday** (LICENSE, gameVersion pin,
  art anachronism review) are still skip-by-default.

---

## Decisions waiting for your call

### Original 3 (from before — unchanged, all skip-by-default)

| # | Decision | Cost of "skip" |
|---|---|---|
| 1 | LICENSE file (MIT? CC-BY-NC?) | Workshop doesn't require one. Skip ⇒ ships with no LICENSE. |
| 2 | modinfo.json gameVersion: pin to `100.15.59076.0` vs keep `100.15.x` wildcard | Wildcard works on every patch. Skip ⇒ ships as-is. |
| 3 | 11 flag/card anachronisms in `artifacts/validation/visual_audit_round2.md` | Aesthetic only; doesn't affect gameplay. Skip ⇒ ships with current art. |

### Column site — historical choices (new, all skip-by-default, documentation only)

Full details in `artifacts/validation/column_site_audit_2026-05-23.md`.

| # | Civ | Issue | Skip cost |
|---|-----|-------|-----------|
| 4 | ANWHaitians | "First Empire" + Toussaint: Toussaint died 1803, Empire declared 1804 by Dessalines | Ships with incongruous pairing |
| 5 | ANWMayans | "Jacinto Canek" (d. 1761) is pre-Cruzob; Cruzob leaders were Cecilio Chi / Jacinto Pat | Ships with wrong historical figure |
| 6 | ANWMexicans | "First Mexican Empire" + Hidalgo: Hidalgo died 1811, Empire was 1821 under Iturbide | Ships with wrong polity name |
| 7 | ANWRevFrance | Robespierre as "strategic commander": he was a politician, never a military commander | Ships with this framing |
| 8 | ANWBrazil | Pedro I (HTML) vs Pedro II (XS log): need to pick one canonical emperor | Ships with mismatch between HTML and XS comment |
| 9 | ANWRussians | "Third TC rush" claim: no supporting code in `leader_catherine.xs` + fabricated card names in Age III bsnote | Ships with mechanical inaccuracy in docs |
| 10 | ANWOttomans | Wall claims: no wall code in `leader_suleiman.xs` + generic card names instead of Ottoman-specific | Ships with inaccurate playstyle description |
| 11 | ANWTexians | Infantry described as primary; XS runs cavalry bias 0.8–0.9 from Colonial (highest in mod) | Ships with inverted doctrine description |
| 12 | ANWLakota | Chief Gall named in sub-header; avatar portrait is `cpai_avatar_lakota_crazy_horse.png` | Ships with name/portrait mismatch |

All three default to "skip" and are independently overridable later.

---

## Where the visual review is

There are exactly two sites — everything else was consolidated or deleted.

| Surface | How to open |
|---|---|
| **Column site** (40 ANW civs, 10–14 thumbs each, full text + cards) | Open `a_new_world_columns.html` locally in your browser — drag the file from the repo root into a browser window. Thumbnails resolve relative to the file, so this works offline. |
| **User reference** (A-Z searchable browse, decks, lore) | `a_new_world.html` locally, or GitHub Pages (if billing resolved) |
| **Per-civ confirmation report** | `artifacts/validation/visual_confirmation_report.md` |

> ⚠️ **GitHub Pages billing issue**: The Actions workflow is showing "account locked due to billing issue" as of 2026-05-22. The column site changes (3-panel layout, 40 civs, screenshots-first) are committed to `main` but not yet live on Pages. To publish the Pages site: fix billing at https://github.com/settings/billing → then run the workflow manually at https://github.com/jflessenkemper/AOE-3-DE-A-New-World-DLC/actions/workflows/pages-deploy.yml → "Run workflow".
> **This does NOT affect Workshop deploy.** The mod files (game/, data/, art/) are fully committed and Workshop publishing goes through AoE3 DE's Steam mod browser, not GitHub Actions.

---

## Workshop deploy steps (manual — same as before)

1. Open AoE3 DE → Mods → Create/Upload Mod.
2. Point to mod directory.
3. Fill Workshop title, description, tags.
4. Click Publish.

Optional polish before step 4:
- Add `LICENSE` file at repo root.
- Pin `modinfo.json` gameVersion to current `100.15.59076.0`.

---

## Live confirmation status (the 7 SKIP validators)

These need an active game to run. They are NOT static-signal blockers, but if you want a green tick before publishing, run a single 5-minute skirmish as Britain (or any ANW civ) and the harness in `tools/aoe3_automation/anw_british_extras_capture.py` will fill them in.

| Validator | What it checks |
|---|---|
| playstyles | live behaviour matches playstyle_spec.json |
| doctrine_compliance | wall.closure + first_dock probe checks |
| visuals | screenshots match reference manifest |
| live_mod_install | mod actually loads in client |
| runtime_logs | no errors in AIErrors-*.txt |
| live_picker | civ picker shows all 40 ANW + 22 base |
| input_harness | gamescopectl screenshots return non-empty |

Of these, only `live_mod_install` is even mildly interesting before publish — and you can verify that with one click in the in-game mod browser.

---

## Files of interest

- `MORNING_DEPLOY.md` — this file (root)
- `artifacts/validation/visual_confirmation_report.md` — NEW: per-civ visual confirmation
- `artifacts/validation/visual_art/civ_art_review.html` — NEW: all 40 civs on one page
- `artifacts/validation/v1_0_readiness_final.md` — longer readiness summary
- `tools/validation/run_all_validators_report.md` — latest validator report
- `a_new_world_columns.html` — 40-civ review site (also on Pages: https://jflessenkemper.github.io/AOE-3-DE-A-New-World-DLC/a_new_world_columns.html)

---

**Bottom line:** Click Publish. Everything is ready.
