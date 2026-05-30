# ANW Backlog Commit Plan
Generated: 2026-05-30

## Current state
- 348 total files in `git status --short`
- 20 files already staged (DLL/preload stack deletions from Task 1)
- 0 secrets found, 0 files >5MB found

## Commit Buckets

### C1 — ALREADY STAGED: chore(harness): remove legacy DLL/preload stack
Files: 20 staged already (dll/, attach.py, dll_client.py, preload/anw_preload.*, tests/test_dll_client.py)
Action: commit immediately.

### C2 — chore(docs): purge superseded testing/build status MD files
Deleted/modified status MDs documenting prior milestones — no longer accurate.
Files (~15):
- D OPTION_B_COMPLETE.md
- D TESTING.md
- D TESTING_AUTOMATION_SUMMARY.md
- D TESTING_COMPLETE_REPORT.md
- D TESTING_FRAMEWORK_STATUS.md
- D TIER2_BUILD_SUMMARY.md
- D TRIGGER_INJECTION_STATUS.md
- D VALIDATION_STATUS.md
- M MOD_HISTORY.md
- M MORNING_DEPLOY.md
- D post_reboot_handoff_2026-04-18.txt
- D session_notes_2026-04-18.txt
- D session_notes_2026-04-20.txt
- D dutch_napoleon_vs_russia_egypt_checklist.txt
- M docs/PORTRAIT_AUDIT_2026-05-04.md
- M docs/RELEASE_QA_PLAN.md
- M artifacts/release/RELEASE_READINESS_v1.0.md

### C3 — chore(branding): rename Legendary Leaders -> A New World across docs/HTML/text
Files (~45): all deleted review_*.html, ANW_NATION_REFERENCE, LEGENDARY_LEADERS_NATION_REFERENCE deleted, RandMaps Legendary Leaders files, review_index.html, a_new_world*.html modified.
Files:
- D LEGENDARY_LEADERS_NATION_REFERENCE.txt
- M ANW_NATION_REFERENCE.txt
- D RandMaps/Legendary Leaders Observer Checklist.md
- D RandMaps/Legendary Leaders Test.md
- D RandMaps/Legendary Leaders Test.xml
- D RandMaps/Legendary Leaders Test.xs
- D RandMaps/legendaryleaders.set
- D review_index.html
- M a_new_world.html
- M a_new_world_columns.html
- M a_new_world_review.html
- M a_new_world_anwbritish_review.html
- D a_new_world_anwargentines_review.html ... (all 38 deleted review HTMLs)
- D blurb_strings.txt
- D blurb_strings_escaped.txt

### C4 — feat(ai): tune per-civ personalities + leader doctrines
Files (~27): all game/ai/ modifications
- M game/ai/aiHeader.xs
- M game/ai/aiLoaderStandard.xs
- M game/ai/anwfrench.personality
- M game/ai/chatsetsmods.anw.xml
- M game/ai/chatsetsmods.xml
- M game/ai/core/aiEliteTactics.xs
- M game/ai/core/aiHCCards.xs
- M game/ai/core/aiLeaderQuotes.xs
- M game/ai/core/aiSetup.xs
- M game/ai/core/aiUtilities.xs
- M game/ai/leaders/leaderCommon.xs + all leader_*.xs
- M game/ai/personalities.xml
- ?? game/ai/core/aiStateSnapshot.xs (new)
- ?? game/ai/core/aiWallKnobsByCiv.xs (new)

### C5 — feat(data): refresh homecity XMLs for all ANW civs
Files (~32): all data/anwhomecity*.xml
Also associated data:
- M data/cards.json
- M data/civmods.xml
- M data/decks.json
- M data/decks_anw.json
- M data/strings/english/stringmods.xml
- M data/techtreemods.xml
- M playstyle_spec.json
- M blurb_database.json
- M civ_string_id_map.json
- ?? PLAYSTYLE_SPECIFICATIONS.json
- ?? enriched_reference.json
- ?? reference_matrix.json
- M docs/CARD_INDEX.txt

### C6 — chore(ci): workflow, harness, and test updates
Files:
- M .github/workflows/playtest-tests.yml
- M .gitmodules
- M tools/aoe3_harness/README.md
- M tools/aoe3_harness/__init__.py
- M tools/aoe3_harness/cli.py
- M tools/aoe3_harness/launch.py
- M tools/validation/build_release_dashboard.py
- M tests/playtest/test_leader_replay_coverage.py
- M tests/playtest/test_replay_probes.py
- M tests/validation/test_validate_civ_crossrefs.py
- M tests/validation/test_validate_civ_homecities.py
- M tests/validation/test_validate_homecity_cards.py
- M tests/validation/test_validate_homecity_visuals.py
- M tests/validation/test_validate_playercolors.py
- ?? tests/validation/test_html_reference.py (new)
- ?? comprehensive_test.sh (new)
- ?? run_anw_overnight_tests.sh (new)
- ?? run_anw_validation_overnight.sh (new)
- ?? run_full_anw_validation.sh (new)
- ?? run_validation_with_gamescope.sh (new)
- ?? VERIFY_FRAMEWORK.sh (new)
- ?? test_scenarios.json (new)

### C7 — chore(artifacts): purge stale visual captures + update manifests
Files: all artifacts/validation/visual_art/ changes (manifests updated, old full screenshots deleted, new crops added for British/French/Russians), plus audit md updates, civ_picker_proof deletions
- D artifacts/civ_picker_proof/01_picker_top.png
- D artifacts/civ_picker_proof/02_in_game_scoreboard.png
- D artifacts/civ_picker_proof/02_scoreboard_BUG_leader_names.png
- All artifacts/validation/visual_art/... (M manifests, D/M images)
- M artifacts/matrix_overnight_20260430_1407.log
- M artifacts/audits/home_city_floating_audit.md
- M artifacts/audits/imperial_playstyle_design_brief.md
- M artifacts/audits/nation_label_flag_audit.md
- M artifacts/audits/post_fix_consistency_audit.md
- M artifacts/audits/test_coverage_audit.md
- M artifacts/validation/ally_deck_compliance.json
- M artifacts/validation/ally_deck_compliance.md
- M artifacts/validation/ally_deck_verification.json
- M artifacts/validation/per_civ_doctrine_audit.md

### C8 — chore(assets): update AI avatar portraits + audio manifest
Files:
- M resources/images/icons/singleplayer/cpai_avatar_*.png (all modified)
- ?? resources/images/icons/singleplayer/cpai_avatar_anwdutch.png (new)
- M resources/audio/revolution_leader_manifest.json

### C9 — chore(stale): delete scenario test files + record game artifacts
Files:
- D Record Game 2026-04-18 14-49-01.age3Yrec
- D Scenario/Legendary Leaders Test.age3Yscn
- D Scenario/legendary-leaders-ai.age3Yscn
- M RandMaps/anwHubTest.xs

### C10 — feat(scenarios): add new ANW test scenario files
Files:
- ?? Scenario/ANEWWORLD_TEST1.age3Yscn
- ?? Scenario/ANEWWORLD_TEST_ANWAI.age3Yscn
- ?? Scenario/ANEWWORLD_TEST_ANWHC.age3Yscn
- ?? Scenario/ANEWWORLD_TEST_STOCK.age3Yscn
- ?? Scenario/TEST_LOOP.md
- ?? RandMaps/user_profile_variant/ (directory)

### C11 — docs: add new documentation and session handoff files
Files:
- ?? TEST_FRAMEWORK_README.md
- ?? QUICKSTART_TEST.md
- ?? docs/OFFLINE_TESTING_2026-05-09.md
- ?? docs/RELEASE_READINESS_2026-05-09.md
- ?? docs/SCENARIO_AUTHORING_PLAYBOOK.md
- ?? docs/SESSION_HANDOFF_2026-05-09.md
- ?? docs/STATE_OF_THE_MOD.md
- ?? docs/VALIDATION_COVERAGE.md
- ?? docs/wiki/ (directory)
- M PORTRAIT_GENERATION_PROMPTS.md

### C12 — chore(llm): add DLL removal plan + coverage artifact
Files:
- ?? .llm/dll_removal_plan.md
- ?? .coverage
