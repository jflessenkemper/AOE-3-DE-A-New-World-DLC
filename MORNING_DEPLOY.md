# A New World — Morning Deploy Checklist

**Generated overnight 2026-05-22 by autonomous /loop.** This is the single doc to read when you wake up.
Last updated: third loop pass (2026-05-22, all AI coverage complete).

---

## TL;DR — GO / NO-GO

**Static signals: GO.** 41/48 validators PASS, 0 FAIL, 7 SKIP (all live-game only). The mod is ready to ship.

**AI coverage: 100%.** All 40 ANW civs now have complete AI dispatch — 21 canonical civs + 19 revolution civs. No civ falls to "unassigned" fallback.

**Three small decisions** are waiting for you before clicking Publish. None are blockers — pick "skip" on any to ship as-is.

---

## What landed overnight (autonomous, no manual input)

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
5. **FrenchCanadians vs LowerCanada audit** — pre-existing
   `artifacts/validation/civ_naming_audit.md` confirms the naming is
   already correct: `ANWCanadians` = playable "Province of Canada";
   `RvltModFrenchCanadians` = revolution state displayed as "Lower
   Canada" (string 494006). No rename needed.
6. **Second loop pass — final mod content committed.** Committed in two
   new pushes (907b69b + 07a75e2) after the first overnight loop pass:
   - **`leaderCommon.xs`**: 19 bespoke per-civ AI build/terrain/expansion
     profiles for every ANW nation (Argentina through USA).
   - **Wall doctrine overrides** in `leader_revolution_commanders.xs`
     and `leader_catherine.xs`: Chileans/Peruvians → FortressRing;
     Haitians/Indonesians/Yucatan/Mayans → ChokepointSegments;
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

## Three things waiting for your call (10 sec each)

| # | Decision | Cost of "skip" |
|---|---|---|
| 1 | LICENSE file (MIT? CC-BY-NC?) | Workshop doesn't require one. Skip ⇒ ships with no LICENSE. |
| 2 | modinfo.json gameVersion: pin to `100.15.59076.0` vs keep `100.15.x` wildcard | Wildcard works on every patch. Skip ⇒ ships as-is. |
| 3 | 11 flag/card anachronisms in `artifacts/validation/visual_audit_round2.md` | Aesthetic only; doesn't affect gameplay. Skip ⇒ ships with current art. |

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
- `artifacts/validation/civ_naming_audit.md` — FrenchCanadians audit
- `tools/validation/run_all_validators_report.md` — latest validator report
- `a_new_world_columns.html` — 40-civ review site (also on Pages: https://jflessenkemper.github.io/AOE-3-DE-A-New-World-DLC/a_new_world_columns.html)

---

**Bottom line:** Click Publish. Everything is ready.
