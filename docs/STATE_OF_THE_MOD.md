# State of the mod — 2026-05-09

Snapshot of project health from the unified validator gate + manual checks.

## Scoreboard

| Layer | State |
|---|---|
| Static art (file existence, HTML cross-refs, civmods consistency) | **GREEN** — 1432/1487 checks PASS, 25 FAIL are artist-work hires-portrait phash mismatches (out-of-scope) |
| stringmods.xml | **GREEN** — 0 duplicate locIDs after dedupe (was 42 conflicting dupes that displayed wrong leader names) |
| Civ definitions structurally complete | **GREEN** — 46 ANW civs, all XMLs well-formed, every flag/portrait/HC reference resolves |
| Civ loadability in lobby picker | **RED** — 21/46 civs load. 25 fail because of "1X" StatsID format. Fix script ready: `tools/migration/fix_civ_loadability.py` |
| stringmods leader name display | **GREEN** — Maurice for Dutch, Wellington for British, etc. (was wrong before dedupe) |
| Test infrastructure (P1 OCR-verified picker) | **GREEN** — 7-9s/civ via cache, ~38% faster than before batched scroll |
| Test infrastructure (opponent picker, P2-P8) | **RED** — clicks land on wrong civ. Workaround: per-civ-match mode (slower but works) |
| Custom scenario binary loading | **RED** — Arxan integrity check rejects all custom binaries. Cannot bypass without engine modding. Workaround: in-game Scenario Editor only. |
| `run_all_validators.py` unified gate | **NEW** — 32 validators wired up; 22 PASS / 8 FAIL on first run |

## Validator gate (32 validators, fast mode, no live game)

```
xml_well_formed              ✓ PASS
packaged_mod                 ✓ PASS
civmods_ui                   ✓ PASS
civ_loadability              ✗ FAIL  (25 civs with 1X StatsID)
civ_homecities               ✓ PASS
civ_crossrefs                ✓ PASS
playstyles                   ✗ FAIL  (uninvestigated)
playercolors                 ✓ PASS
homecity_cards               ✓ PASS
personality_overrides        ✓ PASS
leader_vs_spec               ✗ FAIL  (uninvestigated)
playstyle_modal              ✓ PASS
doctrine_compliance          ✗ FAIL  (uninvestigated)
probes_vs_spec               ✓ PASS
protomods                    ✓ PASS
techtree                     ✓ PASS
xs_scripts                   ✓ PASS
stringtables                 ✓ PASS
art_pixel_perfect            ✓ PASS  (treats artist-work warnings as pass)
art_coverage                 ✓ PASS
homecity_visuals             ✓ PASS
visuals                      ✗ FAIL  (uninvestigated)
terrain_heading              ✓ PASS
dev_subtrees                 ✗ FAIL  (uninvestigated)
html_reference               ✗ FAIL  (uninvestigated)
html_vs_mod                  ✗ FAIL  (uninvestigated)
live_mod_install             - SKIP  (needs game running)
runtime_logs                 - SKIP  (needs game running)
self_civ_loadability         ✓ PASS  10/10 unit tests
self_art_pixel_perfect       ✓ PASS  19/19 unit tests
self_scenario_binary         ✓ PASS  12/12 unit tests
self_test_validator          ✓ PASS  26/26 unit tests
```

Run: `python3 tools/validation/run_all_validators.py`
Reports at: `tools/validation/run_all_validators_report.{md,json}`
Per-validator stdout: `artifacts/validation_runs/run_<ts>/`

## The big blocker

Of all the FAILs above, **`civ_loadability`** is the headline. 25 ANW civs
that don't appear in the lobby picker because of StatsID format choice.
This is the bug that makes the user feel "none of the nations are loading."

**Fix:** `python3 tools/migration/fix_civ_loadability.py --apply` (~30s).
After running and re-syncing the mod (`manage_game.py cycle`), the picker
should show 46 ANW civs.

## Reusable infrastructure shipped this session

- `tools/validation/run_all_validators.py` — single CI gate
- `tools/validation/validate_civ_loadability.py` — catches the StatsID bug
- `tools/migration/fix_civ_loadability.py` — applies the fix (dry-run by default)
- `artifacts/base_game_civs.{json,xml}` — base game civ database extracted from `Data.bar`
- `tools/cardextract/xmb.py` — XMB→XML decoder (was already present, now used for civs.xml)
- `tools/aoe3_automation/picker_civ_order.json` — picker position cache (45/46 civs)
- `tools/aoe3_automation/lobby_driver.py` with `wheel_at_batched()` (3-5x scroll speedup)
- `docs/SESSION_HANDOFF_2026-05-09.md` — handoff with concrete next steps

## What to do tomorrow morning

1. `python3 tools/migration/fix_civ_loadability.py` — review the planned changes
2. `python3 tools/migration/fix_civ_loadability.py --apply` — run the fix
3. `python3 tools/aoe3_automation/manage_game.py cycle` — relaunch with new mod state
4. Verify lobby picker shows 46 ANW civs (no base game)
5. `python3 tools/validation/run_all_validators.py` — re-run the gate
6. Investigate the 7 unrelated validator FAILs
7. Once gate is green: run end-to-end 46-civ AI behavior validation

That's the day-1 critical path. Everything else (visual rendering verifier
extension, opponent picker fix, scenario emitter Arxan workaround) is
followup work that doesn't block the core "all 46 civs in picker" goal.
