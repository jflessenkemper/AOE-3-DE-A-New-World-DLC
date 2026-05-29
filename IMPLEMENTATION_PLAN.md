# ANW Release-Readiness Implementation Plan

---

## Session 2026-05-29 Summary

### Five commits this session

| SHA | Description |
|-----|-------------|
| `ea67a64` | Phase 0 + Phase 1: harness skeleton, pass-roster, DLL pipe client |
| `4e40348` | Phase 2: hook DLL (anw_hook.c/h), input injection, Wine socket IPC |
| `03b6c5d` | Phase 2 hardening: retry backoff, error taxonomy, 53-test suite |
| `08a9625` | Smart walls: chokepoint detection, water/cliff awareness, tier progression |
| `6d82102` | DXGI hook + hot-reload watcher + pixel diff + git-bisect wrapper |

### What is done (all static, no game launch required)

- [x] **Track 1 — Smart Walls** — `game/ai/core/aiBuildingsWalls.xs` rewritten with real chokepoint detection, water/cliff avoidance, wall-tier progression by age, gate-placement logic. All XS static checks pass.
- [x] **Track 4 — FrenchCanadians removed** — `ANWFrenchCanadians` (Papineau) fully purged from sound XMLs, art templates, tools, and docs. `ANWCanadians` (Brock) is the sole active Canadian variant.
- [x] **Track 2a — art_inventory.py extended** — walkers for `diplomacy_panel_art`, `scoreboard_portrait_art`, `postgame_flag_art`, `homecity_visual_scene`, `captured_screenshots`. JSON rows emitted into `tools/validation/art_inventory.json`.
- [x] **Track 2b — build_art_contact_sheet.py extended** — new columns: Diplomacy Portrait, Scoreboard Portrait, Post-game Flag, Custom Leader (hi-res), plus four capture columns (MISSING-until-game-captured placeholders). Top-of-page summary banner shows PASS/MISSING-SOME/MISSING-ALL counts.
- [x] **Track 2c — verify_ally_deck.py** — full XML-vs-JSON deck cross-check for all 40 ANW civs. Produces `ally_deck_compliance.json` + `.md` + `ally_deck_verification.json`. Reports 27/40 PASS, 13 FAIL (card name drift in `decks.json` vs homecity XMLs — see notes below).
- [x] **Telemetry module** — `tools/aoe3_harness/telemetry.py` with `ProbeEvent` dataclass, `parse_log_to_trajectories()`, `emit_html_report()`. SVG inline charts, zero external CDN deps. Registered as `cli.py telemetry parse <log>`.
- [x] **37 new unit tests** — `tools/aoe3_harness/tests/test_telemetry.py`. Full suite: 90/90 PASS.
- [x] **Static validators all PASS** — `static_verify.sh` 21/21, `validate_xs_scripts.py` PASS, `audit_engine_vs_spec.py` 0 mismatches.

### What is deferred to user-driven live verification

The following items require a running game (EXE is `.relaunch_blocked` — do not restore until ready):

- [ ] **In-game art surface captures** — run `python3 -m tools.aoe3_harness.cli capture --civ <TOKEN> --surface <NAME>` per civ once the game is re-enabled. Surfaces: `diplomacy_panel`, `scoreboard_portrait`, `postgame_flag`, `home_city_walking_animation_thumbnail`. The contact sheet shows MISSING placeholders for all 40 civs until these are captured.
- [ ] **Telemetry log parsing from live runs** — once exhibition_runner completes a full 6-pass hubtest, feed `artifacts/validation/ai_playstyle/hubtest_pass*/Age3Log.txt` into `python3 -m tools.aoe3_harness.cli telemetry parse <path>`. Current log files are zero-length (no game was run this session).
- [ ] **OCR ally-deck visual check** — `verify_ally_deck.py` skips visual check when `04_ally_homecity.png` is absent. After in-game captures, re-run to get OCR results.
- [ ] **Ally-deck card-name drift (13 civs)** — `verify_ally_deck.py` reports 13 FAILs with symmetric extra/missing card counts. These are card-rename discrepancies between `decks.json` and the homecity XMLs, not missing decks. Review `ally_deck_compliance.md` and decide whether to update `decks.json` or the XMLs.

### Tomorrow's first move (after EXE is restored)

1. Rename `Age3DE.relaunch_blocked` back to `Age3DE.exe`.
2. Run a quick smoke test: `python3 -m tools.aoe3_harness.cli deploy --check` to deploy the latest mod, then launch one skirmish with ANWBritish vs ANWFrench and confirm the game boots to the lobby without crash (this validates the smart-walls XS changes in a live context).
3. Run `python3 -m tools.aoe3_harness.cli run --pass 1` for pass 1 (7 civs) to get live probe logs, then `python3 -m tools.aoe3_harness.cli telemetry parse artifacts/validation/ai_playstyle/hubtest_pass1_*/Age3Log.txt` to see the first real telemetry report.
4. If pass 1 completes without blocker, queue the remaining 5 passes overnight with `run --all-passes`.
5. After any pass completes, run `python3 tools/validation/build_art_contact_sheet.py` to refresh the contact sheet with updated inventory.

---

## Phase Overview (historical)

### Track 1 — Smart Walls

**Status:** COMPLETE

- `game/ai/core/aiBuildingsWalls.xs` — `llDetectChokepointVector()`, `llSelectWallType()`, water/cliff retreat in `llGetForwardBiasedWallCenter()`, gate placement via chokepoint segment walls.
- Proof source: `game/ai/core/aiExploration.xs:191-200` (existing kbAreaGet* API usage confirmed).
- Static validation: XS syntax PASS, engine_vs_spec 0 mismatches.

### Track 2 — Visual Confirmation Pipeline

**Status:** Static pieces COMPLETE; in-game capture pieces BLOCKED pending EXE restore

- `tools/validation/art_inventory.py` — extended Track 2 surface walkers + captured_screenshots
- `tools/validation/build_art_contact_sheet.py` — extended with 4 surface columns + 4 capture columns + top banner
- `tools/validation/verify_ally_deck.py` — full XML/JSON deck cross-check tool
- `artifacts/validation/visual_art/static_contact_sheet.html` — 422 KB, 40 civs

### Track 3 — AI Playstyle Audit (Telemetry)

**Status:** Parser + renderer COMPLETE; live log population BLOCKED pending game launch

- `tools/aoe3_harness/telemetry.py` — `ProbeEvent`, `parse_log_to_trajectories()`, `emit_html_report()`
- `tools/aoe3_harness/tests/test_telemetry.py` — 37 unit tests, all PASS
- `artifacts/validation/telemetry_report.html` — synthetic demo report (5.6 KB)
- CLI: `python3 -m tools.aoe3_harness.cli telemetry parse <log_path>`

### Track 4 — FrenchCanadians Removed

**Status:** COMPLETE — civ fully purged (2026-05-29)

- `ANWFrenchCanadians` (Papineau) removed from all sound XMLs, art templates, tools, and docs.
- `ANWCanadians` (Brock) remains as the sole active Canadian revolution civ.
- 47 sound XMLs cleaned, 4 art XMLs cleaned, 10+ tool files updated.

---

## Validator Status (2026-05-29)

| Validator | Result |
|-----------|--------|
| `static_verify.sh` | 21/21 PASS |
| `validate_xs_scripts.py` | PASS |
| `audit_engine_vs_spec.py` | 0 mismatches |
| `pytest tools/aoe3_harness/tests/` | 90/90 PASS (+37 from telemetry) |
| `verify_ally_deck.py` | 27/40 PASS, 13 FAIL (card-name drift — see above) |
| `build_art_contact_sheet.py` | 40 civs rendered, 422 KB |

---

## Ally Deck Card-Name Drift — Detail

The 13 FAILs from `verify_ally_deck.py` all show symmetric `extra==missing` counts, meaning the home-city XMLs and `decks.json` reference the same cards under different names (e.g. upgrade cards renamed between mod versions). These are NOT missing decks — every civ has a deck.

To resolve: open `artifacts/validation/ally_deck_compliance.md` and for each failing civ, compare `extra_in_xml` vs `missing_in_xml`. The correct fix is to update `decks.json` to match the XMLs (the XMLs are the engine-authoritative source). This is a one-session cleanup.
